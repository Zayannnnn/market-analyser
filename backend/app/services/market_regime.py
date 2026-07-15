import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from app.db import db
from app.data_sources.market_data import upstox_client
from app.services.technical_indicators import compute_local_indicators

logger = logging.getLogger(__name__)

def get_market_breadth() -> float:
    """
    Computes the market breadth ratio (advancers / (advancers + decliners))
    by querying the active stocks in Firestore.
    Defaults to 0.5 (Neutral) on query failure.
    """
    try:
        stocks_ref = db.collection("stocks").limit(50).get()
        advances = 0
        declines = 0
        for doc in stocks_ref:
            cdata = doc.to_dict()
            # If we don't have direct quote daily change, check indicators
            change = cdata.get("daily_change", 0.0)
            if change > 0.05:
                advances += 1
            elif change < -0.05:
                declines += 1
        
        total = advances + declines
        if total > 0:
            return advances / total
    except Exception as e:
        logger.warning(f"Error computing market breadth from Firestore: {e}")
    return 0.5

def calculate_index_metrics(ticker: str) -> Dict[str, Any]:
    """Fetches index candles and computes moving averages, RSI, and volatility."""
    default_res = {
        "trend": "Neutral",
        "close": 0.0,
        "rsi": 50.0,
        "sma50": 0.0,
        "sma200": 0.0,
        "volatility_annualized": 15.0
    }
    
    try:
        res = upstox_client.fetch_historical_candles(ticker, "day")
        if not res or "candles" not in res:
            logger.warning(f"Failed to fetch index candles for {ticker}")
            return default_res
            
        candles = res["candles"]
        if not candles or len(candles) < 20:
            return default_res
            
        # Reverse to get oldest -> newest chronological order
        candles_reversed = list(candles)
        candles_reversed.reverse()
        
        closes = [float(c[4]) for c in candles_reversed]
        volumes = [float(c[5]) for c in candles_reversed]
        highs = [float(c[2]) for c in candles_reversed]
        lows = [float(c[3]) for c in candles_reversed]
        
        # Calculate local indicators
        indicators = compute_local_indicators(closes, highs, lows, volumes)
        
        close = closes[-1]
        sma50 = indicators.get("sma50", 0.0)
        sma200 = indicators.get("sma200", 0.0)
        rsi = indicators.get("rsi", 50.0)
        
        # Calculate Volatility (standard deviation of daily returns over past 20 days)
        df_closes = pd.Series(closes)
        returns = df_closes.pct_change().dropna()
        recent_returns = returns.tail(20)
        daily_std = recent_returns.std()
        vol_ann = daily_std * np.sqrt(252) * 100 if not np.isnan(daily_std) else 15.0
        
        # Trend classification
        if close > sma50 and sma50 > sma200:
            trend = "Bullish"
        elif close < sma50 and sma50 < sma200:
            trend = "Bearish"
        else:
            trend = "Neutral"
            
        return {
            "trend": trend,
            "close": close,
            "rsi": rsi,
            "sma50": sma50,
            "sma200": sma200,
            "volatility_annualized": vol_ann
        }
    except Exception as e:
        logger.error(f"Error calculating index metrics for {ticker}: {e}")
        return default_res

def determine_market_regime() -> Dict[str, Any]:
    """
    Agent 3 Regime Engine: Evaluates broad market conditions and classifies the Regime
    into one of: Strong Bull, Bull, Neutral, Bear, Strong Bear.
    """
    logger.info("Market Regime Engine evaluating broad index status...")
    
    nifty = calculate_index_metrics("^NSEI")
    banknifty = calculate_index_metrics("^NSEBANK")
    breadth = get_market_breadth()
    
    # Calculate composite score (-3 to +3)
    score = 0
    
    # Nifty Trend Score
    if nifty["trend"] == "Bullish":
        score += 1
    elif nifty["trend"] == "Bearish":
        score -= 1
        
    # BankNifty Trend Score
    if banknifty["trend"] == "Bullish":
        score += 1
    elif banknifty["trend"] == "Bearish":
        score -= 1
        
    # RSI Momentum Score
    if nifty["rsi"] > 58:
        score += 1
    elif nifty["rsi"] < 40:
        score -= 1
        
    # Breadth Score
    if breadth > 0.6:
        score += 1
    elif breadth < 0.4:
        score -= 1
        
    # Volatility factor
    high_vol = (nifty["volatility_annualized"] > 22.0)
    
    # Classify Regime
    if score >= 3:
        regime = "Strong Bull"
    elif score == 1 or score == 2:
        regime = "Bull"
    elif score == 0:
        regime = "Neutral"
    elif score == -1 or score == -2:
        regime = "Strong Bear" if high_vol else "Bear"
    else:
        regime = "Strong Bear"
        
    logger.info(f"Composite Regime Score: {score} | Breadth: {breadth:.2f} | Volatility: {nifty['volatility_annualized']:.1f}% => Regime: {regime}")
    
    return {
        "regime": regime,
        "score": score,
        "nifty_trend": nifty["trend"],
        "nifty_close": round(nifty["close"], 2),
        "nifty_rsi": round(nifty["rsi"], 1),
        "banknifty_trend": banknifty["trend"],
        "banknifty_close": round(banknifty["close"], 2),
        "market_breadth": round(breadth, 2),
        "volatility_annualized": round(nifty["volatility_annualized"], 1),
        "analyzed_at": pd.Timestamp.now().isoformat()
    }
