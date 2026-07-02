import os
import json
import logging
from typing import List, Dict, Any
from app.db import db
from app.data_sources.market_data import get_market_data
from app.ticker_registry import get_stock_master
from app.services.technical_indicators import compute_local_indicators

logger = logging.getLogger(__name__)

def get_monitored_stock_master() -> List[Dict[str, str]]:
    return get_stock_master()

def compute_technical_indicators(ticker: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes technical metrics for a ticker by delegating to the unified technical indicator module.
    """
    history_close = market_data.get("history_close", [])
    history_high = market_data.get("history_high", [])
    history_low = market_data.get("history_low", [])
    history_volume = market_data.get("history_volume", [])
    
    # Delegate calculations to the local reusable module
    indicators = compute_local_indicators(
        history_close=history_close,
        history_high=history_high,
        history_low=history_low,
        history_volume=history_volume
    )
    
    # Format and return a flat dictionary mapping indicators to standard fields
    result = {
        "rsi": indicators["rsi"],
        "macd": indicators["macd_desc"],
        "sma50": indicators["sma50"],
        "sma200": indicators["sma200"],
        "volume_surge": indicators["volume_surge"],
        "breakout_detected": indicators["breakout_detected"],
        "ema20": indicators["ema20"],
        "ema50": indicators["ema50"],
        "atr": indicators["atr"],
        "bollinger_upper": indicators["bollinger_upper"],
        "bollinger_lower": indicators["bollinger_lower"],
        "support": indicators["support"],
        "resistance": indicators["resistance"]
    }
    
    logger.info(
        f"Calculated indicators for {ticker} -> "
        f"Price: {market_data['price']}, RSI: {result['rsi']}, "
        f"SMA50: {result['sma50']}, SMA200: {result['sma200']}, "
        f"MACD: {result['macd']}, Volume Surge: {result['volume_surge']}, "
        f"Breakout: {result['breakout_detected']}. (Fallback used: {market_data.get('fallback_used', False)})"
    )
    
    return result

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
