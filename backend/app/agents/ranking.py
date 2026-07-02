import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from app.db import db

logger = logging.getLogger(__name__)

def calculate_news_score(ticker: str) -> float:
    """
    Calculates News Sentiment Score (0-100) based on recent news articles.
    """
    try:
        news_ref = db.collection("news").where("ticker", "==", ticker).get()
        if not news_ref:
            return 50.0
            
        weighted_sum = 0.0
        weight_total = 0.0
        
        for doc in news_ref:
            article = doc.to_dict()
            sentiment = article.get("sentiment_score", 0.0)
            impact = article.get("impact_level", "low")
            
            multiplier = 0.5
            if impact == "medium":
                multiplier = 1.0
            elif impact == "high":
                multiplier = 1.5
                
            weighted_sum += sentiment * multiplier
            weight_total += multiplier
            
        if weight_total == 0.0:
            return 50.0
            
        avg_sentiment = weighted_sum / weight_total
        news_score = (avg_sentiment + 100) / 2.0
        return float(max(0.0, min(100.0, news_score)))
    except Exception as e:
        logger.error(f"Error calculating news score for {ticker}: {e}")
        return 50.0

def calculate_technical_score(indicators: Dict[str, Any], price: float) -> float:
    """
    Calculates Technical Analysis Score (0-40) based on RSI, MACD, SMAs,
    and volume trend.
    """
    if not indicators:
        return 20.0
        
    score = 0.0
    
    # 1. RSI (Max 10 pts)
    rsi = indicators.get("rsi", 50.0)
    if 50.0 <= rsi <= 70.0:
        score += 10.0
    elif 30.0 <= rsi < 50.0:
        score += 6.0
    elif rsi < 30.0:
        score += 7.0
    else:
        score += 3.0
        
    # 2. MACD (Max 10 pts)
    macd = indicators.get("macd", "")
    if "Bullish Crossover" in macd:
        score += 10.0
    elif "Bullish Trend" in macd:
        score += 8.0
    elif "Bearish Crossover" in macd:
        score += 2.0
    else:
        score += 4.0
        
    # 3. SMA alignment (Max 12 pts)
    sma50 = indicators.get("sma50", 0.0)
    sma200 = indicators.get("sma200", 0.0)
    if price > sma50 > sma200:
        score += 12.0
    elif price > sma50:
        score += 8.0
    elif price > sma200:
        score += 5.0
    else:
        score += 2.0
        
    # 4. Volume trend / breakout (Max 8 pts)
    surge = indicators.get("volume_surge", 1.0)
    if indicators.get("breakout_detected", False):
        score += 8.0
    elif surge >= 1.5:
        score += 6.0
    elif surge >= 1.0:
        score += 4.0
    else:
        score += 2.0
        
    return float(max(0.0, min(40.0, score)))

def _growth_points(value: Any, max_points: float) -> float:
    if value is None:
        return max_points * 0.5
    try:
        val = float(value)
    except (TypeError, ValueError):
        return max_points * 0.5
    if val >= 0.20:
        return max_points
    if val >= 0.10:
        return max_points * 0.8
    if val >= 0.0:
        return max_points * 0.55
    return max_points * 0.2

def calculate_fundamental_score(stock: Dict[str, Any]) -> float:
    """
    Calculates Fundamental Score (0-40) from provider profile fields:
    PE, revenue growth, profit growth, ROE, and debt.
    """
    score = 0.0

    pe = stock.get("pe_ratio")
    try:
        pe_val = float(pe) if pe is not None else None
    except (TypeError, ValueError):
        pe_val = None
    if pe_val is None or pe_val <= 0:
        score += 4.0
    elif 10 <= pe_val <= 30:
        score += 8.0
    elif 30 < pe_val <= 50:
        score += 5.0
    else:
        score += 2.0

    score += _growth_points(stock.get("revenue_growth"), 8.0)
    score += _growth_points(stock.get("profit_growth"), 8.0)

    roe = stock.get("roe")
    try:
        roe_val = float(roe) if roe is not None else None
    except (TypeError, ValueError):
        roe_val = None
    if roe_val is None:
        score += 4.0
    elif roe_val >= 0.18:
        score += 8.0
    elif roe_val >= 0.10:
        score += 6.0
    elif roe_val >= 0:
        score += 3.0
    else:
        score += 1.0

    debt = stock.get("debt_to_equity")
    try:
        debt_val = float(debt) if debt is not None else None
    except (TypeError, ValueError):
        debt_val = None
    if debt_val is None:
        score += 4.0
    elif debt_val <= 50:
        score += 8.0
    elif debt_val <= 100:
        score += 5.0
    else:
        score += 2.0

    return float(max(0.0, min(40.0, score)))

def calculate_stock_score(ticker: str, stock: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates a 0-100 AI score using:
    - Fundamentals: 40 max (PE, revenue growth, profit growth, ROE, debt)
    - Technicals: 40 max (RSI, MACD, SMA50, SMA200, volume trend)
    - News: 20 max (sentiment)
    """
    price = stock.get("current_price", 0.0)
    indicators = stock.get("technical_indicators", {})
    
    fundamental_s = calculate_fundamental_score(stock)
    technical_s = calculate_technical_score(indicators, price)
    news_raw = calculate_news_score(ticker)
    news_s = (news_raw / 100.0) * 20.0
    unified_score = fundamental_s + technical_s + news_s
    
    return {
        "unified_score": int(round(unified_score)),
        "score_breakdown": {
            "fundamental": round(fundamental_s, 1),
            "technical": round(technical_s, 1),
            "news": round(news_s, 1),
            "total": int(round(unified_score)),
        },
        "subscores": {
            "fundamentals": round((fundamental_s / 40.0) * 100.0, 1),
            "news_sentiment": round(news_raw, 1),
            "technical_analysis": round((technical_s / 40.0) * 100.0, 1),
            "valuation": round((fundamental_s / 40.0) * 100.0, 1),
            "growth_potential": round((technical_s / 40.0) * 100.0, 1)
        }
    }

def run_ranking_agent() -> List[Dict[str, Any]]:
    """
    Agent 4 Execution: Loops stocks, calculates weighted unified scores (5-factor model),
    sorts and stores Top 10 results in rankings/snapshots Firestore tables.
    """
    logger.info("Agent 4: Ranking Scorer Agent starting cycle.")
    
    try:
        stocks_ref = db.collection("stocks").get()
    except Exception as e:
        logger.error(f"Error querying active stocks from database: {e}")
        return []
        
    all_scored_stocks = []
    
    for doc in stocks_ref:
        stock = doc.to_dict()
        ticker = doc.id
        
        # Calculate score using unified helper
        scores = calculate_stock_score(ticker, stock)
        
        stock_scored = stock.copy()
        stock_scored["ticker"] = ticker
        stock_scored["subscores"] = scores["subscores"]
        stock_scored["score_breakdown"] = scores["score_breakdown"]
        stock_scored["unified_score"] = scores["unified_score"]
        all_scored_stocks.append(stock_scored)
        
        logger.info(
            f"Scoring results for {ticker} -> "
            f"Fundamentals: {stock_scored['subscores']['fundamentals']}, "
            f"Sentiment: {stock_scored['subscores']['news_sentiment']}, "
            f"Technicals: {stock_scored['subscores']['technical_analysis']}, "
            f"Valuation: {stock_scored['subscores']['valuation']}, "
            f"Growth: {stock_scored['subscores']['growth_potential']} | "
            f"Unified Score: {stock_scored['unified_score']}"
        )
        
        try:
            db.collection("stocks").document(ticker).update({
                "unified_score": stock_scored["unified_score"],
                "subscores": stock_scored["subscores"],
                "score_breakdown": stock_scored["score_breakdown"]
            })
        except Exception as e:
            logger.error(f"Failed to update stock score details for {ticker} in DB: {e}")

    all_scored_stocks.sort(key=lambda s: s.get("unified_score", 0), reverse=True)
    top10_stocks = all_scored_stocks[:10]
    
    # Save Top 10 Leaderboard in Firestore
    timestamp_str = datetime.utcnow().isoformat() + "Z"
    ranking_data = {
        "updated_at": timestamp_str,
        "top_10": top10_stocks
    }
    
    try:
        db.collection("rankings").document("current").set(ranking_data)
        import uuid
        snap_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M')}_{uuid.uuid4().hex[:4]}"
        db.collection("snapshots").document(snap_id).set(ranking_data)
        logger.info("Saved current rankings and snapshots to database.")
    except Exception as e:
        logger.error(f"Failed writing rankings to Firestore: {e}")
        
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "top10.json")
    try:
        with open(output_path, "w") as f:
            json.dump(top10_stocks, f, indent=2)
    except Exception as e:
        logger.error(f"Failed writing top10.json: {e}")
        
    return top10_stocks
