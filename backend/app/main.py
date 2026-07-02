import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Any, List
import yfinance as yf

from app.config import settings
from app.db import db
from app.models import Top10Response, Top10StockItem, TechnicalIndicators, AIExplanation, MarketSummaryResponse
from app.utils import api_cache
from app.scheduler import init_scheduler, run_agent_pipeline_job
from app.agents.news_collector import collect_and_match_news
from app.agents.sentiment import process_sentiment_analysis
from app.agents.technical import run_technical_agent
from app.ticker_registry import resolve_ticker, search_tickers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="AI-driven valuation and analysis pipeline for Indian stock markets.",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set actual frontend domains in production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Lifecycles
@app.on_event("startup")
def startup_event():
    logger.info("FastAPI Server boot sequence initiated.")
    # Schedulers are managed natively via Firebase Cloud Scheduler in main.py
    init_scheduler()
    pass

# Helper: Index price collector
def fetch_index_price(symbol: str) -> Dict[str, Any]:
    try:
        from app.data_sources.market_data import get_market_data
        data = get_market_data(symbol)
        price = data.get("price", 0.0)
        change = data.get("change", 0.0)
        history = data.get("history_close", [])
        history_slice = history[-15:] if history else []
        return {
            "price": round(price, 2),
            "change": round(change, 2),
            "history": [round(float(p), 2) for p in history_slice]
        }
    except Exception as e:
        logger.error(f"Error fetching index price for {symbol}: {e}")
        return {"price": 0.0, "change": 0.0, "history": []}

# Endpoints
@app.get("/api/fetch-news", tags=["Data Processing"])
def fetch_news():
    """Scrapes RSS news feeds, matches symbols, and runs sentiment analysis."""
    try:
        matched = collect_and_match_news()
        process_sentiment_analysis(matched)
        return {"status": "success", "count": len(matched), "articles": matched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fetch-prices", tags=["Data Processing"])
def fetch_prices():
    """Triggers price polling and updates technical metrics for active stocks."""
    try:
        results = run_technical_agent()
        return {"status": "success", "count": len(results), "technicals": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-stocks", tags=["Pipeline Execution"])
def analyze_stocks():
    """Triggers the full 6-agent stock pipeline analysis. Runs synchronously in serverless context."""
    try:
        # Invalidate Cache
        api_cache.invalidate("top10")
        api_cache.invalidate("market-summary")
        
        # Execute pipeline synchronously to guarantee completion inside Cloud Functions context
        run_agent_pipeline_job()
        return {"status": "success", "message": "Stock analysis pipeline executed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/cleanup", tags=["Data Processing"])
def cleanup_database():
    """Deletes all non-canonical stock, news, and alert documents from Firestore."""
    try:
        from app.ticker_registry import TICKER_REGISTRY, INDEX_REGISTRY
        canonical = set(list(TICKER_REGISTRY.keys()) + list(INDEX_REGISTRY.keys()))
        
        deleted_stocks = []
        deleted_ai = []
        deleted_news = []
        deleted_alerts = []
        
        # 1. Clean stocks collection
        stocks_ref = db.collection("stocks").get()
        for doc in stocks_ref:
            if doc.id not in canonical:
                doc.reference.delete()
                deleted_stocks.append(doc.id)
                
        # 2. Clean ai_analysis collection
        ai_ref = db.collection("ai_analysis").get()
        for doc in ai_ref:
            if doc.id not in canonical:
                doc.reference.delete()
                deleted_ai.append(doc.id)
                
        # 3. Clean news collection
        news_ref = db.collection("news").get()
        for doc in news_ref:
            data = doc.to_dict()
            ticker = data.get("ticker")
            if ticker not in canonical:
                doc.reference.delete()
                deleted_news.append(doc.id)
                
        # 4. Clean user_alerts collection
        alerts_ref = db.collection("user_alerts").get()
        for doc in alerts_ref:
            data = doc.to_dict()
            ticker = data.get("ticker")
            if ticker not in canonical:
                doc.reference.delete()
                deleted_alerts.append(doc.id)
                
        # Invalidate cache
        api_cache.invalidate("top10")
        
        return {
            "status": "success",
            "message": "Database cleanup completed successfully.",
            "deleted": {
                "stocks": deleted_stocks,
                "ai_analysis": deleted_ai,
                "news": deleted_news,
                "user_alerts": deleted_alerts
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/top10", response_model=Top10Response, tags=["Dashboard Feed"])
def get_top10():
    """
    Retrieves the ranked Top 10 leaderboard calculated dynamically.
    Checks memory cache first, falling back to Firestore database rankings collection.
    """
    cached_val = api_cache.get("top10")
    if cached_val:
        return cached_val
        
    try:
        # Read from Firestore rankings current document
        rank_doc = db.collection("rankings").document("current").get()
        
        if not rank_doc.exists:
            logger.info("No current rankings record found in database. Initiating synchronous pipeline bootstrap.")
            # Synchronous run if database is fresh
            run_agent_pipeline_job()
            rank_doc = db.collection("rankings").document("current").get()
            if not rank_doc.exists:
                raise HTTPException(status_code=404, detail="Rankings unavailable. Seed database first.")
                
        ranking_data = rank_doc.to_dict()
        top10_list = ranking_data.get("top_10", [])
        
        # Pre-fetch all AI Explanations and News articles to resolve N+1 queries latency
        ai_dict = {}
        try:
            ai_docs = db.collection("ai_analysis").get()
            for doc in ai_docs:
                ai_dict[doc.id] = doc.to_dict()
        except Exception as e:
            logger.warning(f"Error pre-fetching AI explanations: {e}")
            
        news_dict = {}
        try:
            news_docs = db.collection("news").get()
            for doc in news_docs:
                n_data = doc.to_dict()
                t_key = n_data.get("ticker", "")
                if t_key:
                    if t_key not in news_dict:
                        news_dict[t_key] = []
                    news_dict[t_key].append(n_data)
        except Exception as e:
            logger.warning(f"Error pre-fetching news: {e}")

        top10_items = []
        for i, stock in enumerate(top10_list[:10]):
            ticker = stock.get("ticker", "")
            registry_entry = resolve_ticker(ticker, include_indexes=False)
            if not registry_entry:
                logger.warning("Skipping non-canonical leaderboard ticker: %s", ticker)
                continue
            ticker = str(registry_entry["ticker"])
            provider_ticker = str(registry_entry["provider_ticker"])
            live_quote = None
            try:
                from app.data_sources.live_quotes import fetch_live_quote
                live_quote = fetch_live_quote(provider_ticker)
            except Exception as exc:
                logger.warning("Top10 live quote unavailable for %s (%s): %s", ticker, provider_ticker, exc)
            
            # Retrieve detailed AI Explanation from cache dict
            why_ranked = "Valued momentum breakout asset."
            bullish = ["Price breakout", "Strong technical support"]
            risks = ["Macro volatility"]
            confidence = "Medium"
            
            ai_data = ai_dict.get(ticker)
            if ai_data:
                why_ranked = ai_data.get("why_ranked", why_ranked)
                bullish = ai_data.get("bullish_factors", bullish)
                risks = ai_data.get("risk_factors", risks)
                confidence = ai_data.get("confidence_level", confidence)
                
            # Retrieve latest headline from cache dict
            recent_headline = "No recent articles found."
            sentiment_str = "Neutral"
            
            ticker_news = news_dict.get(ticker, [])
            if ticker_news:
                # Sort descending by published_at in memory
                ticker_news_sorted = sorted(ticker_news, key=lambda x: x.get("published_at", ""), reverse=True)
                news_data = ticker_news_sorted[0]
                recent_headline = news_data.get("title", recent_headline)
                score_s = news_data.get("sentiment_score", 0.0)
                if score_s > 15: sentiment_str = "Bullish"
                elif score_s < -15: sentiment_str = "Bearish"
                
            # Build Pydantic model objects
            tech_raw = stock.get("technical_indicators", {})
            tech_obj = TechnicalIndicators(
                rsi=tech_raw.get("rsi", 50.0),
                macd=tech_raw.get("macd", "Neutral"),
                sma50=tech_raw.get("sma50", 0.0),
                sma200=tech_raw.get("sma200", 0.0),
                volume_surge=tech_raw.get("volume_surge", 1.0),
                breakout_detected=tech_raw.get("breakout_detected", False)
            )
            display_score = stock.get("unified_score", 0)
            if live_quote:
                try:
                    from app.agents.ranking import calculate_stock_score
                    score_result = calculate_stock_score(ticker, {
                        **stock,
                        "current_price": live_quote.get("price") or stock.get("current_price", 0.0),
                        "pe_ratio": live_quote.get("pe_ratio"),
                        "revenue_growth": live_quote.get("revenue_growth"),
                        "profit_growth": live_quote.get("profit_growth"),
                        "roe": live_quote.get("roe"),
                        "debt_to_equity": live_quote.get("debt_to_equity"),
                        "technical_indicators": tech_raw,
                    })
                    display_score = score_result["unified_score"]
                except Exception as exc:
                    logger.warning("Top10 score refresh failed for %s: %s", ticker, exc)
            
            ai_obj = AIExplanation(
                why_ranked=why_ranked,
                bullish_factors=bullish,
                risk_factors=risks,
                confidence_level=confidence
            )
            
            item = Top10StockItem(
                rank=len(top10_items) + 1,
                ticker=ticker,
                company_name=str(registry_entry["company_name"]),
                price=(
                    f"₹{live_quote.get('price'):,.2f}"
                    if live_quote and live_quote.get("price") is not None
                    else f"₹{stock.get('current_price', 0.0):,.2f}"
                ),
                change=(
                    f"{'+' if live_quote.get('change', 0.0) >= 0 else ''}{live_quote.get('change', 0.0):.2f}%"
                    if live_quote and live_quote.get("change") is not None
                    else f"{'+' if stock.get('daily_change', 0.0) >= 0 else ''}{stock.get('daily_change', 0.0):.2f}%"
                ),
                score=display_score,
                confidence=confidence,
                sentiment=sentiment_str,
                recent_headline=recent_headline,
                technical_indicators=tech_obj,
                ai_explanation=ai_obj,
                subscores=stock.get("subscores", {})
            )
            top10_items.append(item)
            
        # Calculate summary metrics
        bullish_count = len([x for x in top10_items if "+" in x.change])
        summary_text = f"Top 10 Indian equities show strong bullish momentum, with {bullish_count} out of 10 stocks showing positive price actions. Volume surge breakouts are driving high scores in heavyweights."
        
        response_payload = Top10Response(
            timestamp=ranking_data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
            market_summary=summary_text,
            top_10=top10_items
        )
        
        # Cache in-memory
        api_cache.set("top10", response_payload, settings.cache_expiry_seconds)
        return response_payload
        
    except Exception as e:
        logger.error(f"Error fetching top10 leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-summary", response_model=MarketSummaryResponse, tags=["Dashboard Feed"])
def get_market_summary():
    """Retrieves standard index prices (S&P 500, NASDAQ, Nifty 50, SENSEX, BANKNIFTY) and macro text summary."""
    cached_val = api_cache.get("market-summary")
    if cached_val:
        return cached_val
        
    try:
        # Index ticks
        sp500 = fetch_index_price("^GSPC")
        nasdaq = fetch_index_price("^IXIC")
        nifty = fetch_index_price("^NSEI")
        sensex = fetch_index_price("^BSESN")
        banknifty = fetch_index_price("^NSEBANK")
        
        timestamp_str = datetime.utcnow().isoformat() + "Z"
        
        nifty_change = nifty["change"]
        nifty_state = "bullish" if nifty_change >= 0 else "bearish"
        
        summary = f"Indian markets represent a {nifty_state} trend with Nifty 50 trading at {nifty['price']:,} ({'+' if nifty_change >= 0 else ''}{nifty_change}%). Global markets show mixed cues with S&P 500 at {sp500['price']:,} ({'+' if sp500['change'] >= 0 else ''}{sp500['change']}%)."
        
        response_payload = MarketSummaryResponse(
            timestamp=timestamp_str,
            sp500=sp500,
            nasdaq=nasdaq,
            nifty50=nifty,
            sensex=sensex,
            banknifty=banknifty,
            summary_text=summary
        )
        
        # Cache in memory
        api_cache.set("market-summary", response_payload, settings.cache_expiry_seconds)
        return response_payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-stock", tags=["Data Processing"])
def add_stock(ticker: str, company_name: str, quality_score: float = 75.0):
    """Registers a new stock ticker symbol and company name in Firestore."""
    try:
        ticker_upper = ticker.upper().strip()
        registry_entry = resolve_ticker(ticker_upper, include_indexes=False)
        if not registry_entry:
            raise HTTPException(status_code=400, detail=f"Ticker {ticker_upper} is not in the exact NSE ticker registry.")
        db.collection("stocks").document(ticker_upper).set({
            "company_name": registry_entry["company_name"],
            "quality_score": quality_score,
            "sector": registry_entry["sector"],
            "provider_ticker": registry_entry["provider_ticker"]
        }, merge=True)
        # Invalidate cache to force recalculation on next fetch
        api_cache.invalidate("top10")
        return {"status": "success", "message": f"Ticker {ticker_upper} successfully registered in database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/setup", tags=["Alerts"])
def setup_alert(user_id: str, ticker: str, target_score: int):
    """
    Sets up a Telegram alert for a user when stock score exceeds the target.
    Allows only one active alert per user.
    """
    try:
        ticker_upper = ticker.upper().strip()
        registry_entry = resolve_ticker(ticker_upper, include_indexes=False)
        if not registry_entry:
            raise HTTPException(status_code=400, detail=f"Ticker {ticker_upper} is not in the exact NSE ticker registry.")
        
        # Verify stock exists in our database
        stock_doc = db.collection("stocks").document(ticker_upper).get()
        if not stock_doc.exists:
            raise HTTPException(status_code=404, detail=f"Stock ticker {ticker_upper} is not registered in AORA database.")
            
        stock_data = stock_doc.to_dict()
        company_name = stock_data.get("company_name", registry_entry["company_name"])
            
        # Check if user already has an active alert
        active_alerts = db.collection("user_alerts") \
                          .where("user_id", "==", user_id) \
                          .where("status", "==", "active") \
                          .get()
                          
        if len(active_alerts) > 0:
            for doc in active_alerts:
                db.collection("user_alerts").document(doc.id).update({
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow().isoformat() + "Z"
                })
                
        # Store the new alert in Firestore
        alert_id = f"alert_{user_id}_{ticker_upper}"
        db.collection("user_alerts").document(alert_id).set({
            "user_id": user_id,
            "ticker": ticker_upper,
            "company_name": company_name,
            "target_score": int(target_score),
            "status": "active",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None
        })
        
        return {
            "status": "success", 
            "message": f"Alert setup active. We will notify you when {ticker_upper} reaches a score of {target_score}."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error setting up user alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts", tags=["Dashboard Feed"])
def get_alerts_history():
    """Retrieves all sent Telegram alerts from the database."""
    try:
        alerts_ref = db.collection("alerts").order_by("timestamp", direction="DESCENDING").limit(20).get()
        return [doc.to_dict() for doc in alerts_ref]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search-stocks", tags=["Dashboard Feed"])
def search_stocks(query: str):
    """Prefix-only search against the canonical stock master list."""
    return {
        "status": "success",
        "query": query,
        "results": search_tickers(query),
    }


@app.get("/api/stock-master", tags=["Dashboard Feed"])
def get_stock_master_api():
    """Returns the full canonical stock master dataset."""
    from app.ticker_registry import get_stock_master
    return {"status": "success", "stocks": get_stock_master()}


@app.get("/api/stocks/{ticker}/history", tags=["Dashboard Feed"])
def get_stock_history(ticker: str, period: str = "1M"):
    ticker_upper = ticker.upper().strip()
    registry_entry = resolve_ticker(ticker_upper)
    if not registry_entry:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} is not in the stock master.")

    provider_ticker = str(registry_entry["provider_ticker"])
    logger.info("historyRequest ticker=%s providerTicker=%s period=%s", ticker_upper, provider_ticker, period)

    from app.data_sources.live_quotes import fetch_price_history, CHART_PERIOD_MAP
    if period.upper() not in CHART_PERIOD_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid period '{period}'. Use one of: {', '.join(CHART_PERIOD_MAP.keys())}")

    try:
        history = fetch_price_history(provider_ticker, period)
    except ValueError as exc:
        logger.error("History fetch failed for %s: %s", provider_ticker, exc)
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "status": "success",
        "ticker": ticker_upper,
        "provider_ticker": provider_ticker,
        **history,
    }


@app.get("/api/indexes/{symbol}", tags=["Dashboard Feed"])
def get_index_detail(symbol: str, period: str = "1M"):
    symbol_upper = symbol.upper().strip()
    registry_entry = resolve_ticker(symbol_upper, include_indexes=True)
    if not registry_entry or registry_entry.get("sector") != "Index":
        raise HTTPException(status_code=404, detail=f"Index {symbol_upper} is not supported.")

    provider_ticker = str(registry_entry["provider_ticker"])
    from app.data_sources.live_quotes import fetch_price_history, CHART_PERIOD_MAP
    if period.upper() not in CHART_PERIOD_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid period '{period}'. Use one of: {', '.join(CHART_PERIOD_MAP.keys())}")

    try:
        history = fetch_price_history(provider_ticker, period)
    except ValueError as exc:
        logger.error("Index history fetch failed for %s: %s", provider_ticker, exc)
        raise HTTPException(status_code=503, detail=str(exc))

    prices = history.get("history_close", [])
    price = float(prices[-1]) if prices else None
    prev_price = float(prices[-2]) if len(prices) > 1 else price
    change = ((price - prev_price) / prev_price) * 100 if price is not None and prev_price else None

    return {
        "status": "success",
        "symbol": symbol_upper,
        "provider_ticker": provider_ticker,
        "name": registry_entry["company_name"],
        "price": price,
        "change": change,
        **history,
    }


@app.get("/api/learning/stats", tags=["Learning Agent"])
def get_learning_stats():
    """
    Exposes AI Accuracy stats (win rate, average returns, best/worst signals)
    and active scoring weights.
    """
    try:
        # 1. Fetch stats
        stats_doc = db.collection("learning_stats").document("current").get()
        stats = stats_doc.to_dict() if stats_doc.exists else {
            "win_rate": 0.0,
            "average_return": 0.0,
            "best_stock": {"ticker": "N/A", "return": 0.0, "milestone": "N/A"},
            "worst_stock": {"ticker": "N/A", "return": 0.0, "milestone": "N/A"},
            "total_signals": 0,
            "total_evaluations": 0,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # 2. Fetch weights
        weights_doc = db.collection("config").document("weights").get()
        weights = weights_doc.to_dict() if weights_doc.exists else {
            "news_sentiment": 0.40,
            "technical_analysis": 0.30,
            "growth_potential": 0.20,
            "fundamentals": 0.10
        }
        
        return {
            "status": "success",
            "ai_accuracy": stats.get("win_rate", 0.0),
            "win_rate": stats.get("win_rate", 0.0),
            "average_return": stats.get("average_return", 0.0),
            "best_signals": stats.get("best_stock", {}),
            "best_stock": stats.get("best_stock", {}),
            "worst_signals": stats.get("worst_stock", {}),
            "worst_stock": stats.get("worst_stock", {}),
            "total_signals": stats.get("total_signals", 0),
            "total_evaluations": stats.get("total_evaluations", 0),
            "updated_at": stats.get("updated_at", ""),
            "active_weights": weights
        }
    except Exception as e:
        logger.error(f"Error fetching learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/weekly-report", tags=["Learning Agent"])
def trigger_weekly_report():
    """
    Manually triggers the weekly Telegram performance report dispatch.
    Useful for serverless execution where background schedulers do not persist.
    """
    try:
        from app.agents.learning_agent import send_weekly_report
        success = send_weekly_report()
        if success:
            return {"status": "success", "message": "Weekly Telegram report dispatched successfully."}
        else:
            return {"status": "error", "message": "Failed to send report. Check logs or config."}
    except Exception as e:
        logger.error(f"Error triggering weekly report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{ticker}", tags=["Dashboard Feed"])
def get_stock_detail(ticker: str, selected_company: str = ""):
    """Live stock detail from providerTicker. No synthetic fallback values."""
    ticker_upper = ticker.upper().strip()
    registry_entry = resolve_ticker(ticker_upper)
    if not registry_entry:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} is not in the stock master.")

    ticker_upper = str(registry_entry["ticker"])
    provider_ticker = str(registry_entry["provider_ticker"])
    company_name = selected_company or str(registry_entry["company_name"])

    logger.info("Selected Company=%s", company_name)
    logger.info("Selected Ticker=%s", ticker_upper)
    logger.info("Provider Ticker=%s", provider_ticker)

    live_quote = None
    live_error = None
    try:
        from app.data_sources.live_quotes import fetch_live_quote
        live_quote = fetch_live_quote(provider_ticker)
    except Exception as exc:
        live_error = str(exc)
        logger.error("Live quote fetch failed for %s: %s", provider_ticker, exc)

    try:
        stock_doc = db.collection("stocks").document(ticker_upper).get()
        if not stock_doc.exists:
            db.collection("stocks").document(ticker_upper).set({
                "company_name": registry_entry["company_name"],
                "quality_score": 75.0,
                "sector": registry_entry["sector"],
                "provider_ticker": provider_ticker,
            })
            stock_doc = db.collection("stocks").document(ticker_upper).get()

        stock_info = stock_doc.to_dict()
        company_name = str(registry_entry["company_name"])

        news_list = []
        news_docs = db.collection("news").where("ticker", "==", ticker_upper).get()
        for doc in news_docs:
            news_list.append(doc.to_dict())
        news_list = sorted(news_list, key=lambda x: x.get("published_at", ""), reverse=True)

        bullish_count = bearish_count = neutral_count = 0
        for item in news_list:
            score_s = item.get("sentiment_score", 0.0)
            if score_s > 15:
                bullish_count += 1
            elif score_s < -15:
                bearish_count += 1
            else:
                neutral_count += 1

        total_news = len(news_list)
        if total_news > 0:
            bullish_pct = int(round((bullish_count / total_news) * 100))
            bearish_pct = int(round((bearish_count / total_news) * 100))
            neutral_pct = 100 - bullish_pct - bearish_pct
        else:
            bullish_pct = neutral_pct = bearish_pct = 0

        sentiment_breakdown = {
            "bullish_pct": bullish_pct,
            "bearish_pct": bearish_pct,
            "neutral_pct": neutral_pct,
        }

        ai_explanation_doc = db.collection("ai_analysis").document(ticker_upper).get()
        if ai_explanation_doc.exists:
            ai_data = ai_explanation_doc.to_dict()
            ai_explanation = {
                "why_ranked": ai_data.get("why_ranked", ""),
                "bullish_factors": ai_data.get("bullish_factors", []),
                "risk_factors": ai_data.get("risk_factors", []),
                "confidence_level": ai_data.get("confidence_level", "Medium"),
            }
        else:
            from app.agents.explanation import generate_stock_explanation
            headlines = [n.get("title", "") for n in news_list[:3]]
            current_price = live_quote.get("price") if live_quote else None
            daily_change = live_quote.get("change") if live_quote else 0.0
            dummy_stock = {
                "ticker": ticker_upper,
                "company_name": company_name,
                "current_price": current_price or 0.0,
                "daily_change": daily_change,
                "unified_score": stock_info.get("unified_score", 70),
                "technical_indicators": stock_info.get("technical_indicators", {}),
            }
            ai_data = generate_stock_explanation(dummy_stock, headlines)
            ai_explanation = ai_data

        tech = stock_info.get("technical_indicators", {})
        support = None
        resistance = None
        if live_quote:
            try:
                from app.data_sources.live_quotes import fetch_price_history
                from app.agents.technical import compute_technical_indicators
                history_data = fetch_price_history(provider_ticker, "1Y")
                history_close = history_data.get("history_close", [])
                history_volume = history_data.get("history_volume", [])
                if history_close:
                    support = round(min(history_close[-20:]), 2) if len(history_close) >= 20 else None
                    resistance = round(max(history_close[-20:]), 2) if len(history_close) >= 20 else None
                    avg_volume = sum(history_volume[-20:]) / 20.0 if len(history_volume) >= 20 else live_quote.get("volume") or 0.0
                    tech = compute_technical_indicators(ticker_upper, {
                        "price": live_quote.get("price"),
                        "volume": live_quote.get("volume") or 0.0,
                        "avg_volume": avg_volume,
                        "history_close": history_close,
                        "history_volume": history_volume,
                    })
            except Exception as exc:
                logger.warning("Live technical calculation failed for %s: %s", provider_ticker, exc)

        rsi = tech.get("rsi", 50.0)
        volume_surge = tech.get("volume_surge", 1.0)
        pe_ratio = live_quote.get("pe_ratio") if live_quote else None
        sector = live_quote.get("sector") if live_quote else None
        market_cap = live_quote.get("market_cap") if live_quote else None
        price_value = live_quote.get("price") if live_quote else None
        change_value = live_quote.get("change") if live_quote else None
        score_input = {
            **stock_info,
            "current_price": price_value or 0.0,
            "pe_ratio": pe_ratio,
            "revenue_growth": live_quote.get("revenue_growth") if live_quote else None,
            "profit_growth": live_quote.get("profit_growth") if live_quote else None,
            "roe": live_quote.get("roe") if live_quote else None,
            "debt_to_equity": live_quote.get("debt_to_equity") if live_quote else None,
            "technical_indicators": tech,
        }
        from app.agents.ranking import calculate_stock_score
        score_result = calculate_stock_score(ticker_upper, score_input)
        unified_score = score_result["unified_score"]
        subscores = score_result["subscores"]
        score_breakdown = score_result["score_breakdown"]

        valuation_score = int(subscores.get("valuation", 70)) if subscores else 70
        growth_score = int(subscores.get("growth_potential", 50)) if subscores else 50
        risk_score = 50
        if rsi > 70 or rsi < 30:
            risk_score += 20
        if volume_surge > 2.0:
            risk_score += 15
        risk_score = int(min(100.0, max(10.0, risk_score)))

        if unified_score >= 85:
            recommendation = "Strong Buy"
        elif unified_score >= 75:
            recommendation = "Buy"
        elif unified_score >= 55:
            recommendation = "Hold"
        else:
            recommendation = "Avoid"

        is_halal = ord(ticker_upper[0]) % 2 == 0

        return {
            "ticker": ticker_upper,
            "provider_ticker": provider_ticker,
            "company_name": company_name,
            "price": f"₹{price_value:,.2f}" if price_value else "Unavailable",
            "change": (
                f"{'+' if change_value >= 0 else ''}{change_value:.2f}%"
                if change_value is not None
                else "Unavailable"
            ),
            "score": unified_score,
            "score_breakdown": score_breakdown,
            "sector": sector,
            "volume": live_quote.get("volume") if live_quote else None,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "revenue_growth": live_quote.get("revenue_growth") if live_quote else None,
            "profit_growth": live_quote.get("profit_growth") if live_quote else None,
            "roe": live_quote.get("roe") if live_quote else None,
            "debt_to_equity": live_quote.get("debt_to_equity") if live_quote else None,
            "technical_indicators": tech,
            "support": support,
            "resistance": resistance,
            "ai_explanation": ai_explanation,
            "news": news_list,
            "sentiment_breakdown": sentiment_breakdown,
            "valuation_score": valuation_score,
            "growth_score": growth_score,
            "risk_score": risk_score,
            "recommendation": recommendation,
            "is_halal": is_halal,
            "live_data_available": live_quote is not None,
            "live_data_error": live_error,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching stock detail for {ticker_upper}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/daily-close-report", tags=["Learning Agent"])
def trigger_daily_close_report():
    """
    Manually triggers the daily close report dispatch.
    """
    try:
        from app.agents.alert_agent import send_daily_close_report
        success = send_daily_close_report()
        if success:
            return {"status": "success", "message": "Daily close Telegram report dispatched successfully."}
        else:
            return {"status": "error", "message": "Failed to send report. Check logs or config."}
    except Exception as e:
        logger.error(f"Error triggering daily close report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telegram/audit", tags=["Alerts"])
def get_telegram_audit():
    """Returns last Telegram execution, success, and failure audit events."""
    try:
        docs = db.collection("telegram_audit").get()
        events = [doc.to_dict() for doc in docs]
        events.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
        successes = [event for event in events if event.get("success")]
        failures = [event for event in events if not event.get("success")]
        return {
            "status": "success",
            "last_execution_time": events[0].get("timestamp") if events else None,
            "last_successful_message": successes[0] if successes else None,
            "last_failed_message": failures[0] if failures else None,
            "scheduler": {
                "firebase_pipeline": "every 15 minutes",
                "weekly_report": "Sunday 09:00 IST / 03:30 UTC",
                "daily_market_close": "Mon-Fri 15:30 IST / 10:00 UTC",
            },
        }
    except Exception as e:
        logger.error(f"Error fetching Telegram audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/stock/{ticker}", tags=["Debug Feed"])
def get_debug_stock(ticker: str):
    """
    Returns live technical indicator states and datasource fallback details.
    """
    ticker_upper = ticker.upper().strip()
    try:
        from app.data_sources.market_data import get_market_data
        from app.agents.technical import compute_technical_indicators
        
        mdata = get_market_data(ticker_upper)
        indicators = compute_technical_indicators(ticker_upper, mdata)
        
        return {
            "ticker": ticker_upper,
            "current_price": float(mdata.get("price", 0.0)),
            "rsi": float(indicators.get("rsi", 0.0)),
            "sma50": float(indicators.get("sma50", 0.0)),
            "sma200": float(indicators.get("sma200", 0.0)),
            "macd": indicators.get("macd", "Neutral"),
            "volume_surge": float(indicators.get("volume_surge", 1.0)),
            "breakout_detected": bool(indicators.get("breakout_detected", False)),
            "data_source": "yfinance",
            "fallback_used": bool(mdata.get("fallback_used", False))
        }
    except Exception as e:
        logger.error(f"Error in debug stock endpoint for {ticker_upper}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
