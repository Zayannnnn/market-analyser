import os
import json
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from app.db import db
from app.data_sources.market_data import get_market_data
from app.ticker_registry import get_stock_master

logger = logging.getLogger(__name__)

def get_monitored_stock_master() -> List[Dict[str, str]]:
    return get_stock_master()

def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    """Calculates Relative Strength Index (RSI) using EMA smoothing."""
    if len(series) < period + 1:
        logger.warning(f"RSI calculation failed: insufficient history ({len(series)} < {period + 1}). Returning 50.0.")
        return 50.0
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    # Safeguard for completely flat series (no price movements)
    if avg_gain.iloc[-1] == 0.0 and avg_loss.iloc[-1] == 0.0:
        logger.info("RSI calculation input is flat. Returning 50.0 (Neutral).")
        return 50.0
        
    # Clip loss to avoid division by zero
    avg_loss_clipped = avg_loss.clip(lower=1e-9)
    rs = avg_gain / avg_loss_clipped
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    
    if np.isnan(val):
        logger.warning("RSI calculation yielded NaN value. Returning 50.0.")
        return 50.0
    return float(val)

def calculate_macd(series: pd.Series) -> Dict[str, Any]:
    """Calculates MACD value, signal line, and translates to a trend descriptor."""
    if len(series) < 26:
        logger.warning(f"MACD calculation failed: history size too small ({len(series)} < 26). Returning Neutral.")
        return {"macd_val": 0.0, "signal_val": 0.0, "macd_desc": "Neutral / Flat"}
        
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    
    current_macd = float(macd.iloc[-1])
    current_signal = float(signal.iloc[-1])
    
    # Safeguard: if MACD and signal are both flat/0, return Neutral / Flat
    if current_macd == 0.0 and current_signal == 0.0:
        return {
            "macd_val": 0.0,
            "signal_val": 0.0,
            "macd_desc": "Neutral / Flat"
        }
        
    desc = "Neutral"
    if current_macd > current_signal:
        if len(macd) > 1 and macd.iloc[-2] <= signal.iloc[-2]:
            desc = "Bullish Crossover"
        else:
            desc = "Bullish Trend"
    else:
        if len(macd) > 1 and macd.iloc[-2] >= signal.iloc[-2]:
            desc = "Bearish Crossover"
        else:
            desc = "Bearish Trend"
            
    return {
        "macd_val": current_macd,
        "signal_val": current_signal,
        "macd_desc": desc
    }

def detect_breakout(series: pd.Series, volumes: pd.Series, avg_volume: float) -> bool:
    """Detects channel resistance breakouts (price crossing 20-day high + volume surge)."""
    if len(series) < 21:
        return False
        
    current_close = series.iloc[-1]
    prev_20_max = series.iloc[-21:-1].max()
    current_volume = volumes.iloc[-1]
    
    vol_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Breakout is active if price exceeds 20-day channel peak and volume surge > 1.3x
    return bool(current_close > prev_20_max and vol_ratio > 1.3)

def compute_technical_indicators(ticker: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes technical metrics for a ticker.
    """
    closes = pd.Series(market_data["history_close"])
    volumes = pd.Series(market_data["history_volume"])
    avg_vol = market_data["avg_volume"]
    
    # Calculate indicators
    rsi = calculate_rsi(closes)
    macd_res = calculate_macd(closes)
    
    # SMAs
    sma50 = float(closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean())
    sma200 = float(closes.rolling(200).mean().iloc[-1] if len(closes) >= 200 else closes.mean())
    
    # Vol Surge
    current_vol = market_data["volume"]
    vol_surge = float(current_vol / avg_vol if avg_vol > 0 else 1.0)
    
    # Breakout
    breakout = detect_breakout(closes, volumes, avg_vol)
    
    indicators = {
        "rsi": round(rsi, 2),
        "macd": macd_res["macd_desc"],
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "volume_surge": round(vol_surge, 2),
        "breakout_detected": breakout
    }
    
    logger.info(
        f"Calculated indicators for {ticker} -> "
        f"Price: {market_data['price']}, RSI: {indicators['rsi']}, "
        f"SMA50: {indicators['sma50']}, SMA200: {indicators['sma200']}, "
        f"MACD: {indicators['macd']}, Volume Surge: {indicators['volume_surge']}, "
        f"Breakout: {indicators['breakout_detected']}. (Fallback used: {market_data.get('fallback_used', False)})"
    )
    
    return indicators

def run_technical_agent() -> Dict[str, Dict[str, Any]]:
    """
    Agent 3 Execution: Retrieves prices for all tickers, computes technicals,
    saves output to technical.json and updates 'stocks' details in Firestore.
    """
    logger.info("Agent 3: Technical Analysis Agent starting cycle.")
    
    # 1. Fetch monitored tickers from canonical StockMaster only.
    stock_master = get_monitored_stock_master()
    tickers = [entry["ticker"] for entry in stock_master]
    try:
        for entry in stock_master:
            db.collection("stocks").document(entry["ticker"]).set({
                "company_name": entry["companyName"],
                "sector": entry.get("sector", ""),
                "provider_ticker": entry["providerTicker"],
            }, merge=True)
    except Exception as e:
        logger.error(f"Error seeding canonical stock master: {e}")

    technical_results = {}
    
    # 2. Query market prices and calculate indicators
    for ticker in tickers:
        try:
            mdata = get_market_data(ticker)
            indicators = compute_technical_indicators(ticker, mdata)
            
            # Save technical data
            technical_results[ticker] = indicators
            
            # Update stock prices & technical fields in Firestore
            stock_update = {
                "company_name": mdata.get("name") or next((entry["companyName"] for entry in stock_master if entry["ticker"] == ticker), ticker),
                "provider_ticker": mdata.get("provider_ticker"),
                "sector": mdata.get("sector") or next((entry.get("sector", "") for entry in stock_master if entry["ticker"] == ticker), ""),
                "current_price": mdata["price"],
                "daily_change": mdata["change"],
                "volume": mdata["volume"],
                "avg_volume": mdata["avg_volume"],
                "market_cap": mdata["market_cap"],
                "pe_ratio": mdata["pe_ratio"],
                "revenue_growth": mdata.get("revenue_growth"),
                "profit_growth": mdata.get("profit_growth"),
                "roe": mdata.get("roe"),
                "debt_to_equity": mdata.get("debt_to_equity"),
                "technical_indicators": indicators,
                "history_close": mdata.get("history_close", []),
                "history_volume": mdata.get("history_volume", []),
                "history_dates": mdata.get("history_dates", []),
                "fallback_used": mdata.get("fallback_used", False)
            }
            db.collection("stocks").document(ticker).set(stock_update, merge=True)
            
        except Exception as e:
            logger.error(f"Failed calculating technical analysis for stock {ticker}: {e}")
            
    # Write output to technical.json locally
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "technical.json")
    try:
        with open(output_path, "w") as f:
            json.dump(technical_results, f, indent=2)
        logger.info(f"Agent 3: Technical Agent finished. Saved metrics for {len(technical_results)} tickers to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing technical.json: {e}")
        
    return technical_results
