import logging
import httpx
import datetime
import time
import os
from typing import Dict, Any, Optional, List
from app.config import settings
from app.ticker_registry import resolve_ticker

logger = logging.getLogger(__name__)

class UpstoxClient:
    def __init__(self):
        self.api_key = settings.upstox_api_key
        self.api_secret = settings.upstox_api_secret
        self.base_url = "https://api.upstox.com/v2"
        self.access_token = None
        
    def get_access_token(self) -> Optional[str]:
        """Loads Upstox access token from process env, settings, or Firestore dynamically."""
        # 1. Prioritize environment variable
        token = os.environ.get("UPSTOX_ACCESS_TOKEN")
        if token:
            return token
            
        # 2. Check settings configuration
        if hasattr(settings, "upstox_access_token") and settings.upstox_access_token:
            return settings.upstox_access_token
            
        # 3. Check Firestore configuration config/upstox
        try:
            from app.db import db, MockFirestoreClient
            if not isinstance(db, MockFirestoreClient):
                doc = db.collection("config").document("upstox").get()
                if doc.exists:
                    ddata = doc.to_dict()
                    token = ddata.get("access_token") or ddata.get("accessToken")
                    if token:
                        logger.info("Successfully retrieved Upstox Access Token from Firestore config.")
                        return token
        except Exception as e:
            logger.warning(f"Failed loading Upstox access token from Firestore config: {e}")
            
        return None
        
    def fetch_historical_candles(self, ticker: str, interval: str = "day") -> Optional[Dict[str, Any]]:
        """Queries Upstox API for historical daily candles with retries and timeout."""
        token = self.get_access_token()
        if not token:
            logger.warning(f"Upstox credentials or session tokens missing. Using simulated candles for {ticker}.")
            return None
            
        registry_entry = resolve_ticker(ticker)
        if not registry_entry:
            logger.warning(f"Ticker {ticker} not found in registry.")
            return None
            
        from app.services.instrument_lookup import get_upstox_instrument
        inst = get_upstox_instrument(ticker)
        if not inst:
            logger.warning(f"Ticker {ticker} not found in Upstox instrument master list. Using simulated candles.")
            return None
        instrument_key = inst["instrument_key"]
            
        today = datetime.date.today()
        # Fetch 500 calendar days (approx 350 trading days) to ensure sufficient history for technical indicators
        from_date = today - datetime.timedelta(days=500)
        to_date_str = today.strftime("%Y-%m-%d")
        from_date_str = from_date.strftime("%Y-%m-%d")
        
        # Path parameter order: to_date, then from_date
        url = f"{self.base_url}/historical-candle/{instrument_key}/{interval}/{to_date_str}/{from_date_str}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        # Retry logic: 3 attempts with exponential backoff on retryable codes
        for attempt in range(1, 4):
            try:
                logger.info(f"Upstox Historical Candle request (attempt {attempt}): {url}")
                response = httpx.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    payload = response.json()
                    if payload.get("status") == "success" and "data" in payload:
                        candles = payload["data"].get("candles", [])
                        if candles:
                            logger.info(f"Successfully retrieved {len(candles)} candles from Upstox for {ticker}.")
                            return {
                                "candles": candles,
                                "source": "upstox_api"
                            }
                elif response.status_code == 429:
                    logger.warning(f"Upstox API Rate Limit hit. Retrying in 1s...")
                    time.sleep(1.0)
                else:
                    logger.warning(f"Upstox API returned non-200 code {response.status_code}: {response.text}")
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Connection or timeout error querying Upstox for {ticker}: {e}")
                time.sleep(0.5)
                
        return None

    def generate_simulated_candles(self, ticker: str, days: int = 300) -> Dict[str, Any]:
        """Generates realistic simulated candle arrays for development and fallback testing."""
        import math
        
        seed_val = sum(ord(c) for c in ticker)
        def get_val(i):
            return math.sin(seed_val + i / 8.0) * math.cos(i / 4.0)
            
        base_price = 100.0
        if "GREENPOWER" in ticker:
            base_price = 22.50
        elif "RELIANCE" in ticker:
            base_price = 2450.0
        elif "TCS" in ticker:
            base_price = 3850.0
        elif "INFY" in ticker:
            base_price = 1550.0
        elif "SBIN" in ticker:
            base_price = 780.0
        elif "NSEI" in ticker or "NIFTY" in ticker:
            base_price = 22500.0
        elif "BSESN" in ticker or "SENSEX" in ticker:
            base_price = 73500.0
        elif "NSEBANK" in ticker:
            base_price = 48000.0
        elif "GSPC" in ticker:
            base_price = 5400.0
        elif "IXIC" in ticker:
            base_price = 16000.0
            
        candles = []
        today = datetime.datetime.now()
        for i in range(days):
            dt = (today - datetime.timedelta(days=days - i)).strftime("%Y-%m-%dT09:15:00+05:30")
            wave = get_val(i)
            # Create a slight upward trend over time
            trend = i * (base_price * 0.0005)
            close_p = base_price + trend + wave * (base_price * 0.03)
            # Ensure price stays positive
            close_p = max(1.0, close_p)
            
            open_p = close_p - 0.2 + 0.4 * abs(get_val(i + 1))
            high_p = max(open_p, close_p) + 0.1 + 0.3 * abs(get_val(i + 2))
            low_p = min(open_p, close_p) - 0.1 - 0.3 * abs(get_val(i + 3))
            volume = 1000000.0 + 500000.0 * math.sin(i / 12.0)
            
            # Format matching Upstox response: [timestamp, open, high, low, close, volume, open_interest]
            candles.append([
                dt,
                round(open_p, 2),
                round(high_p, 2),
                round(low_p, 2),
                round(close_p, 2),
                int(volume),
                0
            ])
            
        candles.reverse() # newer candles first (matches Upstox default)
        return {
            "candles": candles,
            "source": "simulated"
        }

upstox_client = UpstoxClient()

def get_profile_from_firestore(ticker: str) -> Dict[str, Any]:
    """Retrieves cached company profile metrics from Firestore with safe fallback details."""
    profile = {
        "market_cap": None,
        "pe_ratio": None,
        "sector": "Utilities",
        "revenue_growth": 0.05,
        "profit_growth": 0.08,
        "roe": 0.12,
        "debt_to_equity": 0.5,
        "company_name": ticker
    }
    
    try:
        from app.db import db, MockFirestoreClient
        if not isinstance(db, MockFirestoreClient):
            doc = db.collection("stocks").document(ticker).get()
            if doc.exists:
                cdata = doc.to_dict()
                profile["company_name"] = cdata.get("company_name") or cdata.get("name") or ticker
                profile["sector"] = cdata.get("sector") or "Utilities"
                
                # Check for fundamentals fields
                if "market_cap" in cdata:
                    profile["market_cap"] = cdata["market_cap"]
                if "pe_ratio" in cdata:
                    profile["pe_ratio"] = cdata["pe_ratio"]
                if "revenue_growth" in cdata:
                    profile["revenue_growth"] = cdata["revenue_growth"]
                if "profit_growth" in cdata:
                    profile["profit_growth"] = cdata["profit_growth"]
                if "roe" in cdata:
                    profile["roe"] = cdata["roe"]
                if "debt_to_equity" in cdata:
                    profile["debt_to_equity"] = cdata["debt_to_equity"]
    except Exception as e:
        logger.warning(f"Error loading company profile cache from Firestore: {e}")
        
    return profile

def get_market_data(ticker: str, period: str = "2y", allow_fallback: bool = True) -> Dict[str, Any]:
    """
    Fetches daily candles and metadata for a given stock symbol.
    Uses Upstox API exclusively; falls back to simulated candles when keys are absent.
    Yahoo Finance is completely removed.
    """
    registry_entry = resolve_ticker(ticker)
    if not registry_entry:
        raise ValueError(f"Unsupported ticker '{ticker}'. Use an exact ticker from the registry.")
        
    ticker = str(registry_entry["ticker"])
    query_ticker = str(registry_entry["provider_ticker"])
    
    # 1. Fetch candles from Upstox (or mock)
    token = upstox_client.get_access_token()
    if token:
        # Account is connected: use REAL Upstox data, fail if it fails
        res = upstox_client.fetch_historical_candles(ticker)
        if not res:
            raise ValueError(f"Upstox Historical Candle API call failed for connected account on {ticker}. Fallbacks are disabled in production mode.")
    else:
        # Offline testing mode: use simulated candles
        logger.warning(f"No Upstox access token found. Running in offline/testing mode with simulated candles.")
        res = upstox_client.generate_simulated_candles(ticker)
        
    candles = res["candles"]
    source = res["source"]
    
    # Upstox returns newest candles first; we reverse them to get oldest -> newest chronological order
    candles_reversed = list(candles)
    candles_reversed.reverse()
    
    # Parse candles: [timestamp, open, high, low, close, volume, open_interest]
    history_close = [float(c[4]) for c in candles_reversed]
    history_volume = [float(c[5]) for c in candles_reversed]
    history_dates = [c[0][:10] for c in candles_reversed]
    history_high = [float(c[2]) for c in candles_reversed]
    history_low = [float(c[3]) for c in candles_reversed]
    
    if not history_close:
        raise ValueError(f"No candle history available for {ticker}")
        
    # Get current price, change, and volume stats
    price = history_close[-1]
    prev_price = history_close[-2] if len(history_close) > 1 else price
    change = ((price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0
    volume = history_volume[-1]
    
    # Calculate average volume (20-day simple average)
    if len(history_volume) >= 20:
        avg_volume = sum(history_volume[-20:]) / 20.0
    else:
        avg_volume = sum(history_volume) / len(history_volume) if history_volume else 1000000.0
        
    # 2. Get profile details from Firestore
    profile = get_profile_from_firestore(ticker)
    company_name = profile.get("company_name") or registry_entry["company_name"]
    
    # Ensure profile metrics are present
    mcap = profile.get("market_cap")
    pe = profile.get("pe_ratio")
    
    return {
        "ticker": ticker,
        "provider_ticker": query_ticker,
        "name": company_name,
        "price": round(float(price), 2),
        "change": round(float(change), 2),
        "volume": float(volume),
        "avg_volume": round(float(avg_volume), 2),
        "market_cap": mcap,
        "pe_ratio": pe,
        "sector": profile.get("sector"),
        "revenue_growth": profile.get("revenue_growth"),
        "profit_growth": profile.get("profit_growth"),
        "roe": profile.get("roe"),
        "debt_to_equity": profile.get("debt_to_equity"),
        "history_close": history_close,
        "history_volume": history_volume,
        "history_high": history_high,
        "history_low": history_low,
        "history_dates": history_dates,
        "fallback_used": (source == "simulated")
    }
