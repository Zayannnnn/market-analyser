import logging
from typing import Any, Dict
from app.ticker_registry import TICKER_REGISTRY, INDEX_REGISTRY
from app.data_sources.market_data import get_market_data

logger = logging.getLogger(__name__)

def _resolve_provider_ticker_to_clean_symbol(provider_ticker: str) -> str:
    """Helper to map providerTicker (e.g. BEL.NS) back to standard stock symbol (e.g. BEL)."""
    # Check tickers
    for k, v in TICKER_REGISTRY.items():
        if v.get("provider_ticker") == provider_ticker:
            return k
            
    # Check indexes
    for k, v in INDEX_REGISTRY.items():
        if v.get("provider_ticker") == provider_ticker:
            return k
            
    # Simple regex fallbacks if not found directly
    clean = provider_ticker.replace(".NS", "").replace("^", "").strip().upper()
    return clean

def fetch_live_quote(provider_ticker: str) -> Dict[str, Any]:
    """Retrieves live price metrics using Upstox under-the-hood. Fulfills the exact API contract."""
    clean_ticker = _resolve_provider_ticker_to_clean_symbol(provider_ticker)
    logger.info(f"fetch_live_quote resolved provider ticker {provider_ticker} to standard symbol {clean_ticker}")
    
    mdata = get_market_data(clean_ticker)
    
    return {
        "price": mdata["price"],
        "change": mdata["change"],
        "volume": mdata["volume"],
        "market_cap": mdata["market_cap"],
        "pe_ratio": mdata["pe_ratio"],
        "sector": mdata["sector"],
        "provider_company_name": mdata["name"],
        "revenue_growth": mdata.get("revenue_growth"),
        "profit_growth": mdata.get("profit_growth"),
        "roe": mdata.get("roe"),
        "debt_to_equity": mdata.get("debt_to_equity")
    }

def fetch_price_history(provider_ticker: str, period: str = "1M") -> Dict[str, Any]:
    """Retrieves historical prices using Upstox candles. Fulfills the exact API contract."""
    clean_ticker = _resolve_provider_ticker_to_clean_symbol(provider_ticker)
    logger.info(f"fetch_price_history resolved provider ticker {provider_ticker} to standard symbol {clean_ticker}")
    
    mdata = get_market_data(clean_ticker, period=period)
    
    return {
        "period": period.upper(),
        "provider_ticker": provider_ticker,
        "history_close": mdata["history_close"],
        "history_volume": mdata["history_volume"],
        "history_dates": mdata["history_dates"]
    }
