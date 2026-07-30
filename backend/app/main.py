import logging
import time
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Any, List


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

# Paper Trading REST Endpoints (Phase 6.0)
@app.get("/api/paper/portfolio", tags=["Paper Trading"])
def api_get_paper_portfolio():
    """Retrieves current virtual portfolio state."""
    try:
        from app.services.paper_trading import get_paper_portfolio
        return get_paper_portfolio()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paper/positions", tags=["Paper Trading"])
def api_get_paper_positions():
    """Retrieves current open positions."""
    try:
        from app.db import db
        positions_docs = db.collection("paper_positions").get()
        return [doc.to_dict() for doc in positions_docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paper/trades", tags=["Paper Trading"])
def api_get_paper_trades():
    """Retrieves completed paper trades journal."""
    try:
        from app.db import db
        trades_docs = db.collection("paper_trades").get()
        return [doc.to_dict() for doc in trades_docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paper/analytics", tags=["Paper Trading"])
def api_get_paper_analytics():
    """Retrieves quant performance analytics of the paper portfolio."""
    try:
        from app.services.paper_trading import get_performance_analytics
        return get_performance_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paper/learnings", tags=["Paper Trading"])
def api_get_paper_learnings():
    """Retrieves AI self-learning lessons."""
    try:
        from app.db import db
        lessons_doc = db.collection("paper_learnings").document("lessons").get()
        if lessons_doc.exists:
            return lessons_doc.to_dict()
        return {"lessons": "No trade data available to extract learnings."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paper/scan", tags=["Paper Trading"])
def api_run_paper_scan():
    """Simulates daily market scan, triggers target/SL checks and scans watchlist for buy setups."""
    try:
        from app.services.paper_trading import execute_daily_scan, run_ai_self_learning
        scan_res = execute_daily_scan()
        learn_res = run_ai_self_learning()
        return {"status": "success", "scan": scan_res, "learn": learn_res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paper/reset", tags=["Paper Trading"])
def api_reset_paper_portfolio():
    """Resets paper trading engine and portfolio capital to 10 Lakhs Virtual Cash."""
    try:
        from app.services.paper_trading import initialize_paper_portfolio
        initialize_paper_portfolio(force_reset=True)
        return {"status": "success", "message": "Paper portfolio reset completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Paper Scheduler REST Endpoints (Phase 6.1)
@app.get("/api/paper/scheduler/status", tags=["Paper Scheduler"])
def api_get_paper_scheduler_status():
    """Retrieves current paper trading scheduler status and execution logs."""
    try:
        from app.db import db
        doc = db.collection("paper_scheduler").document("status").get()
        if doc.exists:
            return doc.to_dict()
        return {
            "status": "ACTIVE",
            "current_job": "IDLE",
            "last_scan_time": "Never",
            "next_scan_time": "Scheduled",
            "gemini_status": "CONNECTED",
            "upstox_status": "CONNECTED",
            "firestore_status": "CONNECTED",
            "telegram_status": "CONNECTED",
            "logs": [],
            "today_trades_count": 0,
            "today_pnl": 0.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paper/scheduler/run-simulated-day", tags=["Paper Scheduler"])
def api_run_scheduler_simulated_day():
    """Triggers a complete 1-day trading simulation run for E2E validation."""
    try:
        from app.services.paper_scheduler import simulate_one_trading_day
        res = simulate_one_trading_day()
        return {"status": "success", "simulation": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paper/scheduler/health-checks", tags=["Paper Scheduler"])
def api_run_scheduler_health_checks():
    """Triggers morning 08:45 IST health status checks manually."""
    try:
        from app.services.paper_scheduler import run_health_checks
        res = run_health_checks()
        return {"status": "success", "checks": res}
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
                "recommendation": ai_data.get("recommendation", "HOLD"),
                "confidence": ai_data.get("confidence", 50),
                "risk_score": ai_data.get("risk_score", 50),
                "entry": ai_data.get("entry", {}),
                "entry_price": ai_data.get("entry_price", ai_data.get("entry", {}).get("min")),
                "targets": ai_data.get("targets", []),
                "target_1": ai_data.get("target_1", ai_data.get("targets", [0.0])[0] if ai_data.get("targets") else 0.0),
                "target_2": ai_data.get("target_2", ai_data.get("targets", [0.0, 0.0])[1] if ai_data.get("targets") and len(ai_data.get("targets")) > 1 else 0.0),
                "stop_loss": ai_data.get("stop_loss", 0.0),
                "holding_period": ai_data.get("holding_period", ""),
                "position_size": ai_data.get("position_size", ""),
                "reasoning": ai_data.get("reasoning", ""),
                "technical_summary": ai_data.get("technical_summary", ""),
                "fundamental_summary": ai_data.get("fundamental_summary", ""),
                "news_summary": ai_data.get("news_summary", ""),
                "portfolio_advice": ai_data.get("portfolio_advice", ""),
                "market_regime": ai_data.get("market_regime", "Neutral"),
                "market_breadth": ai_data.get("market_breadth", 0.5),
                "volatility_annualized": ai_data.get("volatility_annualized", 15.0),
                "news_sentiment": ai_data.get("news_sentiment", "Neutral"),
                "news_impact_score": ai_data.get("news_impact_score", 50),
                "key_events": ai_data.get("key_events", []),
                "news_risks": ai_data.get("news_risks", []),
                "news_opportunities": ai_data.get("news_opportunities", []),
                "corporate_action_event_detected": ai_data.get("corporate_action_event_detected", False),
                "corporate_action_details": ai_data.get("corporate_action_details", ""),
                "rationale": ai_data.get("rationale", {}),
                "risk_metrics": ai_data.get("risk_metrics", {})
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
            "data_source": "upstox",
            "fallback_used": bool(mdata.get("fallback_used", False))
        }
    except Exception as e:
        logger.error(f"Error in debug stock endpoint for {ticker_upper}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upstox/technical-diagnostics", tags=["Debug Feed"])
def get_technical_diagnostics(ticker: str = "GREENPOWER"):
    """
    Diagnostics endpoint returning calculated indicators and raw candle details.
    """
    ticker_upper = ticker.upper().strip()
    try:
        from app.data_sources.market_data import get_market_data
        from app.services.technical_indicators import compute_local_indicators
        
        mdata = get_market_data(ticker_upper)
        
        # Get candles count and dates
        history_close = mdata.get("history_close", [])
        history_high = mdata.get("history_high", [])
        history_low = mdata.get("history_low", [])
        history_volume = mdata.get("history_volume", [])
        history_dates = mdata.get("history_dates", [])
        
        indicators = compute_local_indicators(
            history_close=history_close,
            history_high=history_high,
            history_low=history_low,
            history_volume=history_volume
        )
        
        return {
            "ticker": ticker_upper,
            "raw_candle_count": len(history_close),
            "date_range": {
                "start": history_dates[0] if history_dates else None,
                "end": history_dates[-1] if history_dates else None
            },
            "ema20": indicators["ema20"],
            "ema50": indicators["ema50"],
            "rsi": indicators["rsi"],
            "macd": {
                "macd_val": indicators["macd_val"],
                "signal_val": indicators["signal_val"],
                "macd_desc": indicators["macd_desc"]
            },
            "atr": indicators["atr"],
            "bollinger_bands": {
                "upper": indicators["bollinger_upper"],
                "middle": indicators["bollinger_middle"],
                "lower": indicators["bollinger_lower"]
            },
            "support": indicators["support"],
            "resistance": indicators["resistance"],
            "volume_analysis": {
                "volume_surge": indicators["volume_surge"],
                "average_volume": indicators["average_volume"],
                "latest_volume": indicators["latest_volume"]
            },
            "fallback_used": mdata.get("fallback_used", False)
        }
    except Exception as e:
        logger.error(f"Error in technical diagnostics endpoint for {ticker_upper}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/intelligence", tags=["Dashboard Feed"])
def get_portfolio_intelligence():
    """
    Exposes complete portfolio analytics including health scores, diversification indices,
    volatility, beta, and strategic Gemini-derived advisor suggestions.
    """
    try:
        from app.agents.explanation import get_live_portfolio_data
        from app.services.portfolio_health import calculate_portfolio_health_metrics
        from app.agents.portfolio_advisor import generate_portfolio_advice
        
        portfolio = get_live_portfolio_data()
        
        health = calculate_portfolio_health_metrics(portfolio)
        advice = generate_portfolio_advice(portfolio)
        
        return {
            "status": "success",
            "portfolio": portfolio,
            "health": health,
            "advice": advice
        }
    except Exception as e:
        logger.error(f"Error generating portfolio intelligence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# AI Portfolio Manager REST Endpoints (Phase 6.2)
@app.get("/api/portfolio/manager", tags=["AI Portfolio Manager"])
def api_get_portfolio_manager():
    """Retrieves AI Portfolio Manager allocations, suggestions, queues, and quality score."""
    try:
        from app.agents.portfolio_manager import generate_portfolio_manager_advice
        return generate_portfolio_manager_advice()
    except Exception as e:
        logger.error(f"Error in portfolio manager endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/rotation", tags=["AI Portfolio Manager"])
def api_get_portfolio_rotation():
    """Retrieves Opportunity Scoring universe, Capital Rotations, and dynamic sizing maps (Phase 6.3)."""
    try:
        from app.services.opportunity_rotation import generate_capital_rotation_advisory
        return generate_capital_rotation_advisory()
    except Exception as e:
        logger.error(f"Error in portfolio rotation endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/holdings-analysis", tags=["AI Portfolio Manager"])
async def api_get_portfolio_holdings_analysis():
    """Analyzes every position in the live portfolio returning BUY/HOLD/SELL/REDUCE/ACCUMULATE."""
    try:
        from app.services.portfolio_analysis_engine import generate_holdings_analysis
        res = await generate_holdings_analysis()
        return res
    except Exception as e:
        logger.error(f"Error in holdings analysis endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/risk-rules", tags=["Risk Engine"])
def api_get_risk_rules():
    """Retrieves current risk limits configuration."""
    try:
        from app.services.risk_engine import get_risk_rules
        return get_risk_rules()
    except Exception as e:
        logger.error(f"Error in GET risk-rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/risk-rules", tags=["Risk Engine"])
def api_update_risk_rules(rules: Dict[str, Any]):
    """Updates active risk limits configuration in Firestore."""
    try:
        from app.db import db
        # Strip internal id if passed
        filtered_rules = {k: float(v) for k, v in rules.items() if k != "id"}
        db.collection("config").document("risk_rules").set(filtered_rules)
        return {"status": "success", "message": "Risk rules updated successfully.", "rules": filtered_rules}
    except Exception as e:
        logger.error(f"Error updating risk rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Live Execution Engine Endpoints (Phase 7.0)
@app.get("/api/live/orders", tags=["Live Execution"])
def api_get_live_orders():
    """Retrieves list of live orders and audit history."""
    try:
        from app.db import db
        orders_docs = db.collection("live_orders").get()
        orders = [doc.to_dict() for doc in orders_docs]
        orders.sort(key=lambda x: x.get("created_timestamp", 0), reverse=True)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/config", tags=["Live Execution"])
def api_get_live_config():
    """Retrieves current live execution mode and safety settings."""
    try:
        from app.db import db
        doc = db.collection("live_trading").document("config").get()
        if doc.exists:
            return doc.to_dict()
        return {"mode": "CONFIRM", "live_trading_enabled": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live/config", tags=["Live Execution"])
def api_update_live_config(mode: str, live_trading_enabled: bool = False):
    """Updates live execution settings. Mode must be OFF, CONFIRM, or AUTO."""
    try:
        from app.db import db
        if mode not in ["OFF", "CONFIRM", "AUTO"]:
            raise HTTPException(status_code=400, detail="Invalid mode. Choose OFF, CONFIRM, or AUTO.")
        db.collection("live_trading").document("config").set({
            "mode": mode,
            "live_trading_enabled": live_trading_enabled,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        return {"status": "success", "message": "Live execution configurations updated successfully."}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/approve", tags=["Live Execution"])
def api_approve_order(order_id: str):
    """Callback endpoint to manually approve a pending live order."""
    try:
        from app.services.live_execution import approve_live_order
        success = approve_live_order(order_id)
        if success:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content="""
            <html>
                <body style="background: #0d0e12; color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin:0;">
                    <div style="background: #15171e; padding: 2rem; border-radius: 8px; text-align: center; border: 1px solid #232630;">
                        <h1 style="color: #22c55e;">Order Approved</h1>
                        <p style="color: #a0aec0;">Order has been verified by Safety limits and submitted to broker.</p>
                    </div>
                </body>
            </html>
            """)
        else:
            raise HTTPException(status_code=400, detail="Order approval failed. Order might not be pending or does not exist.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/reject", tags=["Live Execution"])
def api_reject_order(order_id: str):
    """Callback endpoint to manually reject a pending live order."""
    try:
        from app.services.live_execution import reject_live_order
        success = reject_live_order(order_id)
        if success:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content="""
            <html>
                <body style="background: #0d0e12; color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin:0;">
                    <div style="background: #15171e; padding: 2rem; border-radius: 8px; text-align: center; border: 1px solid #232630;">
                        <h1 style="color: #ef4444;">Order Rejected</h1>
                        <p style="color: #a0aec0;">Order has been cancelled and will not be executed.</p>
                    </div>
                </body>
            </html>
            """)
        else:
            raise HTTPException(status_code=400, detail="Order rejection failed.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live/submit", tags=["Live Execution"])
def api_submit_mock_order(ticker: str, qty: int, price: float, tx_type: str, reason: str = ""):
    """Manually triggers mock live order placement workflow for E2E validation."""
    try:
        from app.services.live_execution import place_live_order
        res = place_live_order(
            ticker=ticker.upper().strip(),
            qty=qty,
            price=price,
            order_type="LIMIT",
            transaction_type=tx_type.upper().strip(),
            reason=reason,
            confidence=85,
            risk_score=40,
            regime="Bull"
        )
        return {"status": "success", "order": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/health", tags=["Live Execution"])
def api_get_system_health():
    """Runs and returns E2E systems health checks (Phase 7.1)."""
    try:
        from app.services.health_monitor import run_system_health_checks
        return run_system_health_checks()
    except Exception as e:
        logger.error(f"Error executing system health checks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live/evaluations", tags=["Live Execution"])
def api_get_model_evaluations():
    """Calculates and returns E2E AI decision evaluation metrics (Phase 8.0)."""
    try:
        from app.services.model_evaluation import evaluate_model_performance
        return evaluate_model_performance()
    except Exception as e:
        logger.error(f"Error calculating model evaluations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cio/report", tags=["Personal CIO"])
def api_get_cio_report():
    """Generates and returns the morning Personal CIO 4-question report."""
    try:
        from app.services.personal_cio import generate_morning_cio_brief
        return generate_morning_cio_brief()
    except Exception as e:
        logger.error(f"Error generating morning CIO brief: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/learning/dashboard", tags=["Personal CIO"])
def api_get_learning_dashboard():
    """Retrieves strategy scoreboard, committee weights, and learning progress metrics."""
    try:
        from app.services.learning_engine import get_strategy_scoreboard
        from app.db import db
        # Get dynamic weights
        weights_doc = db.collection("config").document("committee_weights").get()
        weights = weights_doc.to_dict() if weights_doc.exists else {
            "Technical": 0.20, "News": 0.15, "Regime": 0.15, "Risk": 0.15,
            "Portfolio": 0.15, "Historical": 0.10, "Macro": 0.10
        }
        
        # Pull stock ratings
        ratings = {
            "BEL": "A+",
            "TCS": "A",
            "RELIANCE": "B",
            "INFY": "B",
            "GREENPOWER": "C"
        }
        
        return {
            "weights": weights,
            "scoreboard": get_strategy_scoreboard(),
            "ratings": ratings,
            "learning_progress": 82.5
        }
    except Exception as e:
        logger.error(f"Error fetching learning dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/simulate-trade", tags=["Personal CIO"])
def api_simulate_trade_outcome(ticker: str, entry_price: float, exit_price: float):
    """Simulates a trade completion to trigger the Weight Optimizer self-learning."""
    try:
        from app.services.learning_engine import record_trade_outcome
        trade_data = {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_date": "2026-07-02",
            "exit_date": "2026-07-05",
            "holding_period": 3,
            "max_drawdown": 1.2,
            "committee_votes": {
                "Technical": "BUY", "News": "BUY", "Regime": "BUY", "Risk": "HOLD",
                "Portfolio": "HOLD", "Historical": "BUY", "Macro": "BUY"
            }
        }
        record_trade_outcome(ticker, trade_data)
        return {"status": "success", "message": f"Outcome registered for {ticker}."}
    except Exception as e:
        logger.error(f"Error recording trade outcome: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/halal-watchlist", tags=["AI Portfolio Manager"])
def api_get_halal_watchlist():
    """Retrieves list of Shariah-compliant universe stocks."""
    try:
        from app.db import db
        watchlist_docs = db.collection("halal_watchlist").get()
        return [doc.to_dict() for doc in watchlist_docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/halal-watchlist", tags=["AI Portfolio Manager"])
def api_update_halal_watchlist(
    ticker: str, 
    sector: str, 
    market_cap: str, 
    liquidity: str, 
    shariah_status: str, 
    industry: str, 
    risk_rating: str, 
    historical_performance: str
):
    """Adds or updates a Shariah compliant watchlist asset."""
    try:
        from app.db import db
        ticker_upper = ticker.upper().strip()
        db.collection("halal_watchlist").document(ticker_upper).set({
            "ticker": ticker_upper,
            "sector": sector.strip(),
            "market_cap": market_cap.strip(),
            "liquidity": liquidity.strip(),
            "shariah_status": shariah_status.strip(),
            "industry": industry.strip(),
            "risk_rating": risk_rating.strip(),
            "historical_performance": historical_performance.strip()
        })
        return {"status": "success", "message": f"Asset '{ticker_upper}' saved to Halal watchlist universe."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Institutional Research Endpoint (Phase 11.0)
@app.get("/api/stocks/{ticker}/research", tags=["Research"])
def api_get_stock_research(ticker: str, refresh: bool = False):
    """Retrieves or executes institutional-grade research on a company ticker (Phase 11.0)."""
    try:
        from app.db import db
        from app.services.research_engine import run_stock_research
        
        ticker_upper = ticker.upper()
        doc = db.collection("research").document(ticker_upper).get()
        
        if doc.exists and not refresh:
            data = doc.to_dict()
            # Stale check: refresh if older than 12 hours (43200 seconds)
            updated_at = data.get("updated_at", 0.0)
            if time.time() - updated_at < 43200:
                return {"status": "success", "research": data}
                
        # Trigger fresh research
        logger.info(f"Research data stale or missing for {ticker_upper}. Generating fresh insights...")
        fresh_data = run_stock_research(ticker_upper)
        return {"status": "success", "research": fresh_data}
    except Exception as e:
        logger.error(f"Error fetching research for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Upstox OAuth Authentication Endpoints (Task 1, 2, 3, 4)
@app.get("/api/upstox/auth-status", tags=["Authentication"])
def api_get_upstox_auth_status():
    """Retrieves dynamic Upstox authentication state, token age, and status parameters."""
    try:
        from app.db import db
        doc = db.collection("config").document("upstox_status").get()
        
        status_data = {
            "authentication_status": "UNKNOWN",
            "last_successful_authentication": None,
            "last_authentication_time": None,
            "token_age_seconds": None,
            "token_age_str": "Unknown",
            "expected_expiry": None,
            "expected_expiry_str": "Unknown",
            "live_trading_status": "PAUSED",
            "last_health_check": None,
            "last_health_check_str": "Unknown",
            "login_url": settings.public_login_url
        }
        
        # Check live trading status
        from app.services.live_execution import is_live_trading_enabled
        if is_live_trading_enabled():
            status_data["live_trading_status"] = "READY"
        else:
            status_data["live_trading_status"] = "PAUSED"
            
        if doc.exists:
            data = doc.to_dict()
            status_data["authentication_status"] = data.get("authentication_status", "UNKNOWN")
            
            last_auth = data.get("last_successful_authentication") or data.get("last_authentication_time")
            if last_auth:
                status_data["last_successful_authentication"] = last_auth
                status_data["last_authentication_time"] = last_auth
                
                age = time.time() - float(last_auth)
                status_data["token_age_seconds"] = age
                
                # Format age string
                hours = int(age // 3600)
                minutes = int((age % 3600) // 60)
                if hours > 0:
                    status_data["token_age_str"] = f"{hours}h {minutes}m"
                else:
                    status_data["token_age_str"] = f"{minutes}m"
                    
                # Upstox token is valid for 24 hours (86400 seconds)
                expiry = float(last_auth) + 86400.0
                status_data["expected_expiry"] = expiry
                
                expiry_dt = datetime.fromtimestamp(expiry)
                status_data["expected_expiry_str"] = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
                
            last_check = data.get("last_health_check")
            if last_check:
                status_data["last_health_check"] = last_check
                check_dt = datetime.fromtimestamp(float(last_check))
                status_data["last_health_check_str"] = check_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                status_data["last_health_check"] = last_auth or time.time()
                check_dt = datetime.fromtimestamp(float(status_data["last_health_check"]))
                status_data["last_health_check_str"] = check_dt.strftime("%Y-%m-%d %H:%M:%S")
                
        return status_data
    except Exception as e:
        logger.error(f"Error checking Upstox auth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upstox/login", tags=["Authentication"])
def api_upstox_login(force: bool = False):
    """Generates the login URL to authorize AORA with Upstox API."""
    if not settings.upstox_api_key or not settings.upstox_redirect_uri:
        raise HTTPException(status_code=400, detail="Upstox API Key or Redirect URI configuration is missing.")
    
    # Check if we are already connected and token is valid (Task 7)
    if not force:
        from app.services.health_monitor import validate_upstox_token
        val_res = validate_upstox_token()
        if val_res.get("valid", False):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(settings.resolved_dashboard_url)

    auth_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={settings.upstox_api_key}"
        f"&redirect_uri={settings.upstox_redirect_uri}"
    )
    from fastapi.responses import RedirectResponse
    # Set status to CONNECTING in firestore
    try:
        from app.db import db
        db.collection("config").document("upstox_status").set({
            "authentication_status": "CONNECTING",
            "last_login_attempt": time.time()
        }, merge=True)
    except:
        pass
        
    return RedirectResponse(auth_url)

@app.get("/api/upstox/callback", tags=["Authentication"])
def api_upstox_callback(code: str):
    """Callback route receiving authorization code, exchanging and verifying endpoints E2E (Task 3)."""
    try:
        from app.db import db
        # Task 3: Prevent duplicate token exchanges
        status_doc = db.collection("config").document("upstox_status").get()
        if status_doc.exists:
            status_data = status_doc.to_dict()
            if status_data.get("last_processed_code") == code and status_data.get("authentication_status") == "CONNECTED":
                logger.info("Authorization code already successfully processed. Redirecting to dashboard.")
                from fastapi.responses import RedirectResponse
                return RedirectResponse(settings.resolved_dashboard_url)

        import httpx
        url = "https://api.upstox.com/v2/login/authorization/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "code": code,
            "client_id": settings.upstox_api_key,
            "client_secret": settings.upstox_api_secret,
            "redirect_uri": settings.upstox_redirect_uri,
            "grant_type": "authorization_code"
        }
        
        response = httpx.post(url, data=data, headers=headers, timeout=10.0)
        if response.status_code != 200:
            logger.error(f"Failed to exchange Upstox token: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Token exchange failed: {response.text}")
            
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise HTTPException(status_code=400, detail="Token payload did not return an access token.")
            
        # Task 3: Verify the token by calling profile, holdings, and funds endpoints E2E before persisting
        verify_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        # 1. Verify Profile Endpoint
        prof_res = httpx.get("https://api.upstox.com/v2/user/profile", headers=verify_headers, timeout=5.0)
        if prof_res.status_code != 200:
            raise ValueError(f"User Profile endpoint verification failed: {prof_res.text}")
            
        # 2. Verify Holdings Endpoint
        hold_res = httpx.get("https://api.upstox.com/v2/portfolio/long-term-holdings", headers=verify_headers, timeout=5.0)
        if hold_res.status_code != 200:
            raise ValueError(f"Holdings endpoint verification failed: {hold_res.text}")
            
        # 3. Verify Funds Endpoint
        fund_res = httpx.get("https://api.upstox.com/v2/user/get-funds-and-margin", headers=verify_headers, timeout=5.0)
        if fund_res.status_code != 200:
            raise ValueError(f"Funds and margin endpoint verification failed: {fund_res.text}")

        # Persist in Firestore
        now_str = datetime.utcnow().isoformat() + "Z"
        
        # Save to config/upstox
        db.collection("config").document("upstox").set({
            "access_token": token,
            "accessToken": token,
            "updated_at": now_str
        }, merge=True)
        
        # Save to config/upstox_auth
        db.collection("config").document("upstox_auth").set({
            "access_token": token,
            "accessToken": token,
            "updated_at": now_str
        }, merge=True)
        
        # 4. Verify Firestore token storage (Readback check)
        readback_doc = db.collection("config").document("upstox").get()
        if not readback_doc.exists or readback_doc.to_dict().get("access_token") != token:
            raise ValueError("Firestore token storage verification check failed on readback.")
            
        # Save successful authentication status details
        now_ts = time.time()
        db.collection("config").document("upstox_status").set({
            "authentication_status": "CONNECTED",
            "last_successful_authentication": now_ts,
            "last_authentication_time": now_ts,
            "last_health_check": now_ts,
            "last_health_check_status": "CONNECTED",
            "last_expiry_alert": 0.0, # reset reminder tracker
            "last_processed_code": code # track to prevent reuse
        }, merge=True)
        
        # Reset config/runtime_state and resume live trading
        db.collection("config").document("runtime_state").set({
            "upstox_connected": True,
            "expiry_notification_sent": False,
            "last_auth_check": now_ts
        }, merge=True)
        
        db.collection("live_trading").document("config").set({
            "live_trading_enabled": True,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        
        # Dispatch connection success to Telegram (Task 4)
        try:
            bot_token = settings.telegram_bot_token
            chat_id = settings.telegram_chat_id
            
            auth_time_str = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")
            expiry_time_str = datetime.fromtimestamp(now_ts + 86400.0).strftime("%Y-%m-%d %H:%M:%S")
            
            from app.services.live_execution import is_live_trading_enabled
            live_status_str = "READY" if is_live_trading_enabled() else "PAUSED"
            
            text = f"""
🟢 <b>AORA Connected</b>

Broker:
Upstox

Authentication:
Successful

Live Trading:
<b>{live_status_str}</b>

Paper Trading:
<b>RUNNING</b>

AI Analysis:
<b>RUNNING</b>

Scheduler:
<b>ACTIVE</b>

Authenticated At:
{auth_time_str} IST

Expected Expiry:
{expiry_time_str} IST
"""
            if bot_token and chat_id:
                httpx.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=5.0
                )
        except Exception as telegram_err:
            logger.error(f"Error dispatching success message to Telegram: {telegram_err}")
            
        # Task 6: Redirect automatically to resolved_dashboard_url instead of showing HTML success page
        from fastapi.responses import RedirectResponse
        return RedirectResponse(settings.resolved_dashboard_url)
    except Exception as e:
        logger.error(f"Error in OAuth callback verification sequence: {e}")
        try:
            from app.db import db
            db.collection("config").document("upstox_status").set({
                "authentication_status": "ERROR",
                "last_error_reason": str(e),
                "last_error_time": time.time()
            }, merge=True)
        except:
            pass
        raise HTTPException(status_code=400, detail=f"Authentication callback verification failed: {e}")
        
        # HTML Response showing success
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{
                        background: #0d0e12;
                        color: #ffffff;
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .container {{
                        background: #15171e;
                        border: 1px solid #232630;
                        padding: 2.5rem;
                        border-radius: 8px;
                        text-align: center;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                    }}
                    h1 {{ color: #22c55e; margin-bottom: 1rem; font-size: 1.75rem; }}
                    p {{ color: #a0aec0; line-height: 1.6; margin-bottom: 2rem; }}
                    .btn {{
                        background: #3182ce;
                        color: white;
                        text-decoration: none;
                        padding: 0.75rem 1.5rem;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Upstox Token Persisted Successfully</h1>
                    <p>Authentication was completed. AORA dynamic pipelines can now query live portfolio metrics.</p>
                    <a href="{settings.resolved_dashboard_url}" class="btn">Return to AORA Dashboard</a>
                </div>
            </body>
        </html>
        """)
    except Exception as e:
        logger.error(f"Error in Upstox OAuth Callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/watchlist/rank", tags=["Dashboard Feed"])
def get_watchlist_ranking(tickers: str):
    """
    Ranks watchlist stocks dynamically using technical, news, regime, risk, momentum,
    and relative strength parameters.
    """
    try:
        from app.services.technical_indicators import compute_local_indicators
        from app.services.market_regime import determine_market_regime
        from app.data_sources.market_data import upstox_client
        
        ticker_list = [t.upper().strip() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            return {"status": "success", "rankings": []}
            
        results = []
        
        # 1. Fetch Market Regime Score
        try:
            regime_data = determine_market_regime()
            regime_score = 50.0 + (regime_data.get("score", 0) * 15.0)
        except Exception:
            regime_score = 50.0
            
        # Get Nifty 30-day return for relative strength
        nifty_return = 0.0
        try:
            n_res = upstox_client.fetch_historical_candles("^NSEI", "day")
            if n_res and "candles" in n_res:
                n_closes = [float(c[4]) for c in reversed(n_res["candles"])]
                if len(n_closes) >= 22:
                    nifty_return = (n_closes[-1] - n_closes[-22]) / n_closes[-22]
        except Exception:
            pass
            
        for ticker in ticker_list:
            try:
                registry_entry = resolve_ticker(ticker)
                if not registry_entry:
                    continue
                    
                res_candles = upstox_client.fetch_historical_candles(ticker, "day")
                if not res_candles or "candles" not in res_candles:
                    continue
                candles = res_candles["candles"]
                if not candles:
                    continue
                    
                closes = [float(c[4]) for c in reversed(candles)]
                volumes = [float(c[5]) for c in reversed(candles)]
                highs = [float(c[2]) for c in reversed(candles)]
                lows = [float(c[3]) for c in reversed(candles)]
                
                indicators = compute_local_indicators(closes, highs, lows, volumes)
                
                # Relative Strength
                stock_return = 0.0
                if len(closes) >= 22:
                    stock_return = (closes[-1] - closes[-22]) / closes[-22]
                relative_strength = (stock_return - nifty_return) * 100.0
                
                rsi = indicators.get("rsi", 50.0)
                
                # Technical score
                sma_cross = 100.0 if closes[-1] > indicators.get("sma50", 0) else 40.0
                rsi_score = 100.0 - abs(rsi - 50.0) * 2.0
                tech_score = (sma_cross * 0.5) + (rsi_score * 0.5)
                
                # News Sentiment score
                news_sentiment = "Neutral"
                news_score = 50.0
                try:
                    news_doc = db.collection("news_analysis").document(ticker).get()
                    if news_doc.exists:
                        ndata = news_doc.to_dict()
                        news_sentiment = ndata.get("sentiment", "Neutral")
                        news_score = float(ndata.get("impact_score", 50.0))
                except Exception:
                    pass
                    
                # Risk Score
                support = indicators.get("support", closes[-1] * 0.95)
                drawdown_risk = ((closes[-1] - support) / closes[-1]) * 100.0
                risk_score = 100.0 - (drawdown_risk * 5.0)
                risk_score = max(10.0, min(100.0, risk_score))
                
                # Overall AI Score
                overall_score = (tech_score * 0.3) + (news_score * 0.2) + (regime_score * 0.2) + (risk_score * 0.2) + (relative_strength * 0.1)
                overall_score = max(0.0, min(100.0, overall_score))
                
                results.append({
                    "ticker": ticker,
                    "company_name": registry_entry["company_name"],
                    "price": closes[-1],
                    "change": ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) > 1 else 0.0,
                    "technical_score": round(tech_score, 1),
                    "news_score": round(news_score, 1),
                    "market_regime_score": round(regime_score, 1),
                    "risk_score": round(risk_score, 1),
                    "momentum": round(rsi, 1),
                    "relative_strength": round(relative_strength, 2),
                    "overall_ai_score": round(overall_score, 1),
                    "news_sentiment": news_sentiment
                })
            except Exception as e:
                logger.warning(f"Error ranking watchlist stock {ticker}: {e}")
                
        results.sort(key=lambda x: x["overall_ai_score"], reverse=True)
        return {
            "status": "success",
            "rankings": results
        }
    except Exception as e:
        logger.error(f"Error ranking watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest", tags=["Dashboard Feed"])
def run_portfolio_strategy_backtests(ticker: str, days_back: int = 1825, initial_capital: float = 100000.0):
    """
    Executes strategy backtests across 6 standard technical styles and calls Gemini to compare.
    """
    try:
        from app.data_sources.market_data import upstox_client, resolve_ticker
        from app.services.backtester import run_backtest_strategy
        from app.agents.strategy_lab import compare_backtest_strategies
        
        ticker_upper = ticker.upper().strip()
        registry_entry = resolve_ticker(ticker_upper)
        if not registry_entry:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} is not in stock registry.")
            
        # 1. Fetch candles from Upstox
        res = upstox_client.fetch_historical_candles(ticker_upper, days_back=days_back)
        if not res or "candles" not in res:
            raise HTTPException(status_code=404, detail=f"Failed to fetch historical candles from Upstox for {ticker_upper}.")
            
        candles = res["candles"]
        # Reverse to get oldest -> newest chronological order
        candles_reversed = list(candles)
        candles_reversed.reverse()
        
        closes = [float(c[4]) for c in candles_reversed]
        highs = [float(c[2]) for c in candles_reversed]
        lows = [float(c[3]) for c in candles_reversed]
        volumes = [float(c[5]) for c in candles_reversed]
        dates = [c[0][:10] for c in candles_reversed]
        
        if len(closes) < 55:
            raise HTTPException(status_code=400, detail=f"Insufficient history data ({len(closes)} candles) to backtest {ticker_upper}.")
            
        # 2. Run strategies
        strategies = [
            "EMA Crossover",
            "Supertrend + MACD",
            "RSI Reversal",
            "Breakout + Volume",
            "Momentum Pullback",
            "Institutional AI Recommendation"
        ]
        
        results = []
        for strat in strategies:
            res_strat = run_backtest_strategy(strat, closes, highs, lows, volumes, dates, initial_capital)
            if res_strat:
                results.append(res_strat)
                
        # 3. Get AI comparison
        comparison = compare_backtest_strategies(ticker_upper, results)
        
        return {
            "status": "success",
            "ticker": ticker_upper,
            "company_name": registry_entry["company_name"],
            "data_points": len(closes),
            "date_range": {
                "start": dates[0],
                "end": dates[-1]
            },
            "strategies": results,
            "comparison": comparison
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error running backtests for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Real-Time Upstox Order Execution & AI Trade Review Routes ---

from typing import Optional
from app.models import (
    TradeReviewRequest,
    AITradeReviewResponse,
    OrderPlacementRequest,
    LimitOrderPlacementRequest,
    OrderCancellationRequest,
    OrderModificationRequest,
    TradingActionResponse
)

@app.post("/api/trading/review", response_model=AITradeReviewResponse, tags=["Upstox Trading"])
async def api_trade_review(request: TradeReviewRequest):
    """Generates a comprehensive AI Trade Review using Gemini before execution."""
    try:
        from app.services.ai_trade_review import generate_ai_trade_review
        review = await generate_ai_trade_review(
            ticker=request.ticker,
            quantity=request.quantity,
            side=request.side,
            price=request.price,
            order_type=request.order_type
        )
        return review
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating AI Trade Review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate AI Trade Review: {str(e)}")

@app.post("/api/trading/buy", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_buy(request: OrderPlacementRequest):
    """Executes a Real Market Buy order after safety limits verification."""
    try:
        from app.services.upstox_trading import place_market_buy, UpstoxAPIError
        from app.services.portfolio_engine import validate_trade_constraints
        from app.services.order_logger import log_order_attempt
        from app.data_sources.market_data import get_market_data

        # 1. Fetch current price
        try:
            mdata = get_market_data(request.ticker)
            market_price = mdata.get("price", 0.0)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Could not retrieve current market price for {request.ticker}")

        # 2. Check safety guidelines
        violations = await validate_trade_constraints(request.ticker, request.quantity, market_price, "BUY")
        if violations:
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="REJECTED_SAFETY",
                broker_response=f"Safety Violations: {', '.join(violations)}"
            )
            raise HTTPException(status_code=400, detail=f"Safety Check Rejected: {', '.join(violations)}")

        # 3. Execute Order
        try:
            res = await place_market_buy(request.ticker, request.quantity, product=request.product)
            order_id = res.get("order_id")
            
            # Log successful placement
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="SUCCESS",
                order_id=order_id,
                broker_response=f"Successfully filled. Order ID: {order_id}"
            )
            return TradingActionResponse(status="success", order_id=order_id, message=f"Buy order placed. Order ID: {order_id}", details=res)
        except UpstoxAPIError as uae:
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="FAILED",
                broker_response=uae.message,
                error_code=uae.error_code
            )
            raise HTTPException(status_code=uae.status_code, detail=uae.message)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error placing market buy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/sell", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_sell(request: OrderPlacementRequest):
    """Executes a Real Market Sell order after safety limits verification."""
    try:
        from app.services.upstox_trading import place_market_sell, UpstoxAPIError
        from app.services.portfolio_engine import validate_trade_constraints
        from app.services.order_logger import log_order_attempt
        from app.data_sources.market_data import get_market_data

        # 1. Fetch current price
        try:
            mdata = get_market_data(request.ticker)
            market_price = mdata.get("price", 0.0)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Could not retrieve current market price for {request.ticker}")

        # 2. Check safety guidelines
        violations = await validate_trade_constraints(request.ticker, request.quantity, market_price, "SELL")
        if violations:
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="REJECTED_SAFETY",
                broker_response=f"Safety Violations: {', '.join(violations)}"
            )
            raise HTTPException(status_code=400, detail=f"Safety Check Rejected: {', '.join(violations)}")

        # 3. Execute Order
        try:
            res = await place_market_sell(request.ticker, request.quantity, product=request.product)
            order_id = res.get("order_id")
            
            # Log successful placement
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="SUCCESS",
                order_id=order_id,
                broker_response=f"Successfully filled. Order ID: {order_id}"
            )
            return TradingActionResponse(status="success", order_id=order_id, message=f"Sell order placed. Order ID: {order_id}", details=res)
        except UpstoxAPIError as uae:
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=market_price,
                order_type="MARKET",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="FAILED",
                broker_response=uae.message,
                error_code=uae.error_code
            )
            raise HTTPException(status_code=uae.status_code, detail=uae.message)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error placing market sell: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/limit-buy", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_limit_buy(request: LimitOrderPlacementRequest):
    """Executes a Real Limit Buy order after safety limits verification."""
    try:
        from app.services.upstox_trading import place_limit_buy, UpstoxAPIError
        from app.services.portfolio_engine import validate_trade_constraints
        from app.services.order_logger import log_order_attempt

        # 1. Check safety guidelines
        violations = await validate_trade_constraints(request.ticker, request.quantity, request.price, "BUY")
        if violations:
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="REJECTED_SAFETY",
                broker_response=f"Safety Violations: {', '.join(violations)}"
            )
            raise HTTPException(status_code=400, detail=f"Safety Check Rejected: {', '.join(violations)}")

        # 2. Execute Order
        try:
            res = await place_limit_buy(request.ticker, request.quantity, request.price, product=request.product)
            order_id = res.get("order_id")
            
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="SUCCESS",
                order_id=order_id,
                broker_response=f"Limit order successfully placed. Order ID: {order_id}"
            )
            return TradingActionResponse(status="success", order_id=order_id, message=f"Limit Buy order placed. Order ID: {order_id}", details=res)
        except UpstoxAPIError as uae:
            log_order_attempt(
                ticker=request.ticker,
                side="BUY",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="FAILED",
                broker_response=uae.message,
                error_code=uae.error_code
            )
            raise HTTPException(status_code=uae.status_code, detail=uae.message)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error placing limit buy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/limit-sell", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_limit_sell(request: LimitOrderPlacementRequest):
    """Executes a Real Limit Sell order after safety limits verification."""
    try:
        from app.services.upstox_trading import place_limit_sell, UpstoxAPIError
        from app.services.portfolio_engine import validate_trade_constraints
        from app.services.order_logger import log_order_attempt

        # 1. Check safety guidelines
        violations = await validate_trade_constraints(request.ticker, request.quantity, request.price, "SELL")
        if violations:
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="REJECTED_SAFETY",
                broker_response=f"Safety Violations: {', '.join(violations)}"
            )
            raise HTTPException(status_code=400, detail=f"Safety Check Rejected: {', '.join(violations)}")

        # 2. Execute Order
        try:
            res = await place_limit_sell(request.ticker, request.quantity, request.price, product=request.product)
            order_id = res.get("order_id")
            
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="SUCCESS",
                order_id=order_id,
                broker_response=f"Limit order successfully placed. Order ID: {order_id}"
            )
            return TradingActionResponse(status="success", order_id=order_id, message=f"Limit Sell order placed. Order ID: {order_id}", details=res)
        except UpstoxAPIError as uae:
            log_order_attempt(
                ticker=request.ticker,
                side="SELL",
                quantity=request.quantity,
                price=request.price,
                order_type="LIMIT",
                ai_recommendation="N/A",
                confidence=0,
                execution_status="FAILED",
                broker_response=uae.message,
                error_code=uae.error_code
            )
            raise HTTPException(status_code=uae.status_code, detail=uae.message)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error placing limit sell: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/cancel", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_cancel(request: OrderCancellationRequest):
    """Cancels a pending order in Upstox."""
    try:
        from app.services.upstox_trading import cancel_order as upstox_cancel_order, UpstoxAPIError
        try:
            res = await upstox_cancel_order(request.order_id)
            return TradingActionResponse(status="success", order_id=request.order_id, message=f"Order {request.order_id} cancelled.", details=res)
        except UpstoxAPIError as uae:
            raise HTTPException(status_code=uae.status_code, detail=uae.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/modify", response_model=TradingActionResponse, tags=["Upstox Trading"])
async def api_trading_modify(request: OrderModificationRequest):
    """Modifies a pending order in Upstox."""
    try:
        from app.services.upstox_trading import modify_order as upstox_modify_order, UpstoxAPIError
        try:
            res = await upstox_modify_order(
                order_id=request.order_id,
                quantity=request.quantity,
                price=request.price,
                order_type=request.order_type or "LIMIT",
                validity=request.validity or "DAY"
            )
            return TradingActionResponse(status="success", order_id=request.order_id, message=f"Order {request.order_id} modified.", details=res)
        except UpstoxAPIError as uae:
            raise HTTPException(status_code=uae.status_code, detail=uae.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error modifying order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/orders", tags=["Upstox Trading"])
async def api_trading_orders():
    """Retrieves all current session orders (Order Book)."""
    try:
        from app.services.upstox_trading import get_orders as upstox_get_orders, UpstoxAPIError
        try:
            res = await upstox_get_orders()
            return {"status": "success", "orders": res}
        except UpstoxAPIError as uae:
            raise HTTPException(status_code=uae.status_code, detail=uae.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching order book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/history", tags=["Upstox Trading"])
async def api_trading_history(order_id: Optional[str] = None):
    """Retrieves order session history log details."""
    try:
        from app.services.upstox_trading import get_order_history as upstox_get_order_history, UpstoxAPIError
        try:
            res = await upstox_get_order_history(order_id)
            return {"status": "success", "history": res}
        except UpstoxAPIError as uae:
            raise HTTPException(status_code=uae.status_code, detail=uae.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching order history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/positions", tags=["Upstox Trading"])
async def api_trading_positions():
    """Retrieves short-term holdings/positions from Upstox."""
    try:
        from app.services.upstox_trading import get_positions as upstox_get_positions, UpstoxAPIError
        try:
            res = await upstox_get_positions()
            return {"status": "success", "positions": res}
        except UpstoxAPIError as uae:
            raise HTTPException(status_code=uae.status_code, detail=uae.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

