import logging
import yfinance as yf
import httpx
import datetime
from typing import Dict, Any, Optional
from app.config import settings
from app.ticker_registry import resolve_ticker

logger = logging.getLogger(__name__)

class UpstoxClient:
    def __init__(self):
        self.api_key = settings.upstox_api_key
        self.api_secret = settings.upstox_api_secret
        self.base_url = "https://api.upstox.com/v2"
        self.access_token = None
        
    def fetch_ohlc(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.access_token:
            logger.debug("Upstox credentials or session tokens missing. Delegating query to yfinance.")
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
            instrument = f"NSE_EQ|{ticker}"
            response = httpx.get(
                f"{self.base_url}/market-quote/quotes?symbol={instrument}", 
                headers=headers, 
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json().get("data", {}).get(instrument, {})
                logger.info(f"Successfully retrieved simple quote from Upstox API for {ticker}.")
                return {
                    "price": data.get("last_price"),
                    "change": data.get("net_change_percent"),
                    "volume": data.get("volume"),
                    "avg_volume": None
                }
        except Exception as e:
            logger.error(f"Error querying Upstox API: {e}")
        return None

upstox_client = UpstoxClient()

def _profile_fields(info: Dict[str, Any]) -> Dict[str, Any]:
    raw_mcap = info.get("marketCap")
    raw_pe = info.get("trailingPE") or info.get("forwardPE")
    return {
        "market_cap": (float(raw_mcap) / 1e9) if raw_mcap else None,
        "pe_ratio": float(raw_pe) if raw_pe else None,
        "sector": info.get("sector"),
        "revenue_growth": info.get("revenueGrowth"),
        "profit_growth": info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"),
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
    }

def get_market_data(ticker: str, period: str = "2y", allow_fallback: bool = True) -> Dict[str, Any]:
    """
    Fetches real-time price, volume, moving history, and statistics for a given stock symbol.
    Attempts Upstox first, then direct Chart HTTP queries (2-year range), then standard yfinance.
    Uses exact registry mappings only. It may fall back to cached Firestore
    data for scheduled jobs, but never generates synthetic prices.
    """
    registry_entry = resolve_ticker(ticker)
    if not registry_entry:
        raise ValueError(f"Unsupported ticker '{ticker}'. Use an exact ticker from the registry.")

    ticker = str(registry_entry["ticker"])
    query_ticker = str(registry_entry["provider_ticker"])

    logger.info(
        "Market data exact mapping: resolvedTicker=%s providerTicker=%s period=%s",
        ticker,
        query_ticker,
        period,
    )
    
    # 1. Attempt Upstox (NSE Equities)
    upstox_data = upstox_client.fetch_ohlc(ticker)
    if upstox_data and upstox_data.get("price"):
        logger.info(f"Retrieved stock {ticker} from Upstox API.")
        try:
            t = yf.Ticker(query_ticker)
            hist = t.history(period="2y")
            info = t.info
            profile = _profile_fields(info)
            logger.info(f"Successfully fetched Upstox support history for {ticker}. History size: {len(hist)}")
            return {
                "ticker": ticker,
                "provider_ticker": query_ticker,
                "name": info.get("longName", ticker),
                "price": float(upstox_data["price"]),
                "change": float(upstox_data["change"]),
                "volume": float(upstox_data["volume"]),
                "avg_volume": float(hist['Volume'].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else float(upstox_data["volume"]),
                **profile,
                "history_close": hist['Close'].astype(float).tolist(),
                "history_volume": hist['Volume'].astype(float).tolist(),
                "history_dates": hist.index.strftime('%Y-%m-%d').tolist(),
                "fallback_used": False
            }
        except Exception as e:
            logger.warning(f"Failed to fetch Upstox support history: {e}. Falling back fully to yfinance HTTP.")

    # 2. Query Yahoo Finance Chart API directly via HTTP to bypass rate limit throttling
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{query_ticker}?range={period}&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
        
        logger.info(f"HTTP GET query: {url}")
        response = httpx.get(url, headers=headers, timeout=12.0)
        logger.info(f"HTTP Chart API status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            result = data["chart"]["result"][0]
            meta = result["meta"]
            
            price = meta.get("regularMarketPrice")
            volume = meta.get("regularMarketVolume", 0.0)
            name = meta.get("longName") or meta.get("shortName") or ticker
            
            timestamps = result.get("timestamp", [])
            quote = result.get("indicators", {}).get("quote", [{}])[0]
            closes_raw = quote.get("close", [])
            volumes_raw = quote.get("volume", [])
            
            logger.info(f"Direct Chart API retrieved {len(timestamps)} timestamps for {query_ticker}.")
            
            history_close = []
            history_volume = []
            history_dates = []
            
            last_valid_close = price
            last_valid_volume = volume if volume is not None else 1000000.0
            valid_close_seen = False
            
            for idx, t_val in enumerate(timestamps):
                # Close
                c_val = closes_raw[idx]
                if c_val is not None:
                    last_valid_close = float(c_val)
                    valid_close_seen = True
                if last_valid_close is None:
                    continue
                history_close.append(last_valid_close)
                
                # Volume
                v_val = volumes_raw[idx]
                if v_val is not None:
                    last_valid_volume = float(v_val)
                history_volume.append(last_valid_volume)
                
                # Date
                dt = datetime.datetime.utcfromtimestamp(t_val).strftime('%Y-%m-%d')
                history_dates.append(dt)
                
            if not history_close or not valid_close_seen:
                raise ValueError("Chart API returned empty history arrays")
                
            if price is None:
                price = history_close[-1]
            if volume is None:
                volume = history_volume[-1]
                
            prev_price = history_close[-2] if len(history_close) > 1 else price
            daily_change = ((price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0
            
            # Calculate 20-day average volume
            if len(history_volume) >= 20:
                avg_volume = sum(history_volume[-20:]) / 20.0
            else:
                avg_volume = sum(history_volume) / len(history_volume) if history_volume else 1000000.0
                
            profile = {
                "market_cap": None,
                "pe_ratio": None,
                "sector": None,
                "revenue_growth": None,
                "profit_growth": None,
                "roe": None,
                "debt_to_equity": None,
            }
            try:
                info = yf.Ticker(query_ticker).info
                profile = _profile_fields(info)
                name = info.get("longName") or name
            except Exception as info_error:
                logger.warning(f"Unable to enrich provider profile for {query_ticker}: {info_error}")
            
            logger.info(f"Direct Chart parse SUCCESS for {ticker}. Price: {price}, Change: {daily_change:.2f}%")
            logger.info(f"Raw yfinance response for {ticker} (Direct Chart): Close history length={len(history_close)}, first_price={history_close[0] if history_close else None}, last_price={history_close[-1] if history_close else None}")
            return {
                "ticker": ticker,
                "provider_ticker": query_ticker,
                "name": name,
                "price": float(price),
                "change": float(daily_change),
                "volume": float(volume),
                "avg_volume": float(avg_volume),
                **profile,
                "history_close": history_close,
                "history_volume": history_volume,
                "history_dates": history_dates,
                "fallback_used": False
            }
        else:
            logger.warning(f"Direct Chart query returned non-200 status: {response.status_code}. Checking alternative server.")
    except Exception as e:
        logger.warning(f"Direct Chart API fetch failed for {query_ticker} (caused fallback): {e}", exc_info=True)
        
    # 2.5 Try query1 server fallback
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{query_ticker}?range={period}&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        logger.info(f"HTTP query1 GET: {url}")
        response = httpx.get(url, headers=headers, timeout=12.0)
        if response.status_code == 200:
            data = response.json()
            result = data["chart"]["result"][0]
            meta = result["meta"]
            price = meta.get("regularMarketPrice")
            volume = meta.get("regularMarketVolume", 0.0)
            name = meta.get("longName") or meta.get("shortName") or ticker
            timestamps = result.get("timestamp", [])
            quote = result.get("indicators", {}).get("quote", [{}])[0]
            closes_raw = quote.get("close", [])
            volumes_raw = quote.get("volume", [])
            
            history_close = []
            history_volume = []
            history_dates = []
            last_valid_close = price
            last_valid_volume = volume if volume is not None else 1000000.0
            valid_close_seen = False
            
            for idx, t_val in enumerate(timestamps):
                c_val = closes_raw[idx]
                if c_val is not None:
                    last_valid_close = float(c_val)
                    valid_close_seen = True
                if last_valid_close is None:
                    continue
                history_close.append(last_valid_close)
                
                v_val = volumes_raw[idx]
                if v_val is not None:
                    last_valid_volume = float(v_val)
                history_volume.append(last_valid_volume)
                
                dt = datetime.datetime.utcfromtimestamp(t_val).strftime('%Y-%m-%d')
                history_dates.append(dt)
                
            if not history_close or not valid_close_seen:
                raise ValueError("query1 Chart API returned empty history arrays")
            if price is None: price = history_close[-1]
            if volume is None: volume = history_volume[-1]
            prev_price = history_close[-2] if len(history_close) > 1 else price
            daily_change = ((price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0
            avg_volume = sum(history_volume[-20:]) / 20.0 if len(history_volume) >= 20 else volume
            profile = {
                "market_cap": None,
                "pe_ratio": None,
                "sector": None,
                "revenue_growth": None,
                "profit_growth": None,
                "roe": None,
                "debt_to_equity": None,
            }
            try:
                info = yf.Ticker(query_ticker).info
                profile = _profile_fields(info)
                name = info.get("longName") or name
            except Exception as info_error:
                logger.warning(f"Unable to enrich provider profile for {query_ticker}: {info_error}")
            
            logger.info(f"query1 parse SUCCESS for {ticker}.")
            logger.info(f"Raw yfinance response for {ticker} (query1): Close history length={len(history_close)}, first_price={history_close[0] if history_close else None}, last_price={history_close[-1] if history_close else None}")
            return {
                "ticker": ticker,
                "provider_ticker": query_ticker,
                "name": name,
                "price": float(price),
                "change": float(daily_change),
                "volume": float(volume),
                "avg_volume": float(avg_volume),
                **profile,
                "history_close": history_close,
                "history_volume": history_volume,
                "history_dates": history_dates,
                "fallback_used": False
            }
    except Exception as e:
        logger.warning(f"query1 fallback failed (caused fallback): {e}", exc_info=True)

    # 3. Fallback to standard yfinance client
    try:
        logger.info(f"Standard yfinance client query for {query_ticker} (period: {period})")
        t = yf.Ticker(query_ticker)
        hist = t.history(period=period)
        if hist.empty:
            raise ValueError(f"Yahoo Finance standard returned empty history for symbol: {query_ticker}")
            
        info = t.info
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        daily_change = ((current_price - prev_price) / prev_price) * 100
        volume = hist['Volume'].iloc[-1]
        avg_volume = hist['Volume'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else hist['Volume'].mean()
        profile = _profile_fields(info)
        
        logger.info(f"Standard yfinance SUCCESS for {ticker}. Price: {current_price}")
        logger.info(f"Raw yfinance response for {ticker} (Standard client): Close history length={len(hist['Close'])}, first_price={hist['Close'].iloc[0]}, last_price={hist['Close'].iloc[-1]}")
        return {
            "ticker": ticker,
            "provider_ticker": query_ticker,
            "name": info.get("longName", ticker),
            "price": float(current_price),
            "change": float(daily_change),
            "volume": float(volume),
            "avg_volume": float(avg_volume),
            **profile,
            "history_close": hist['Close'].astype(float).tolist(),
            "history_volume": hist['Volume'].astype(float).tolist(),
            "history_dates": hist.index.strftime('%Y-%m-%d').tolist(),
            "fallback_used": False
        }
    except Exception as e:
        logger.error(f"Error fetching market data for {query_ticker} via yfinance standard (caused fallback): {e}", exc_info=True)
        if not allow_fallback:
            raise ValueError(f"Live provider data unavailable for exact ticker {ticker} ({query_ticker}).")

        # Firestore lookup fallback to prevent mock structure
        try:
            from app.db import db
            cached_stock = db.collection("stocks").document(ticker).get()
            if cached_stock.exists:
                cdata = cached_stock.to_dict()
                if "current_price" in cdata and "history_close" in cdata and cdata.get("history_close"):
                    logger.info(f"Retrieved cached history series from Firestore fallback for {ticker}.")
                    return {
                        "ticker": ticker,
                        "provider_ticker": query_ticker,
                        "name": cdata.get("company_name", str(registry_entry["company_name"])),
                        "price": float(cdata["current_price"]),
                        "change": float(cdata.get("daily_change", 0.0)),
                        "volume": float(cdata.get("volume", 1000000.0)),
                        "avg_volume": float(cdata.get("avg_volume", 1000000.0)),
                        "market_cap": cdata.get("market_cap"),
                        "pe_ratio": cdata.get("pe_ratio"),
                        "sector": cdata.get("sector"),
                        "revenue_growth": cdata.get("revenue_growth"),
                        "profit_growth": cdata.get("profit_growth"),
                        "roe": cdata.get("roe"),
                        "debt_to_equity": cdata.get("debt_to_equity"),
                        "history_close": cdata["history_close"],
                        "history_volume": cdata.get("history_volume", []),
                        "history_dates": cdata.get("history_dates", []),
                        "fallback_used": True
                    }
        except Exception as fe:
            logger.error(f"Failed to fetch Firestore fallback: {fe}")
            
        raise ValueError(f"Provider and cache data unavailable for exact ticker {ticker} ({query_ticker}).")
