import os
import gzip
import httpx
import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "upstox_instruments_cache.json"
)

INDEX_MAP = {
    "NIFTY50": {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "isin": "NIFTY50",
        "exchange": "NSE",
        "trading_symbol": "Nifty 50",
        "name": "Nifty 50 Index"
    },
    "BANKNIFTY": {
        "instrument_key": "NSE_INDEX|Nifty Bank",
        "isin": "BANKNIFTY",
        "exchange": "NSE",
        "trading_symbol": "Nifty Bank",
        "name": "Nifty Bank Index"
    },
    "SENSEX": {
        "instrument_key": "BSE_INDEX|SENSEX",
        "isin": "SENSEX",
        "exchange": "BSE",
        "trading_symbol": "SENSEX",
        "name": "SENSEX Index"
    }
}

def load_cache() -> Dict[str, Dict[str, Any]]:
    """Loads the cached instruments from disk if it exists."""
    if os.path.exists(CACHE_FILE_PATH):
        try:
            with open(CACHE_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read instrument cache file: {e}")
    return {}

def save_cache(cache_data: Dict[str, Dict[str, Any]]):
    """Saves the instruments dictionary to the local data directory."""
    os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
    try:
        with open(CACHE_FILE_PATH, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save instrument cache file: {e}")

def reload_upstox_instrument_master() -> Dict[str, Dict[str, Any]]:
    """
    Downloads and parses the official Upstox NSE instrument master.
    Builds a lookup mapping for equities.
    """
    logger.info("Downloading official Upstox NSE instrument master...")
    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        if response.status_code != 200:
            logger.error(f"Failed to download instrument master. Status code: {response.status_code}")
            return {}
            
        content = gzip.decompress(response.content)
        instruments = json.loads(content)
        
        new_cache = {}
        for inst in instruments:
            segment = inst.get("segment")
            inst_type = inst.get("instrument_type")
            trading_symbol = inst.get("trading_symbol")
            
            # Map equities only (underlying or EQ standard listings)
            if segment == "NSE_EQ" and inst_type == "EQ" and trading_symbol:
                new_cache[trading_symbol.upper()] = {
                    "instrument_key": inst.get("instrument_key"),
                    "isin": inst.get("isin"),
                    "exchange": inst.get("exchange", "NSE"),
                    "trading_symbol": trading_symbol,
                    "name": inst.get("name")
                }
                
        # Cache metadata
        new_cache["_metadata"] = {
            "timestamp": time.time(),
            "count": len(new_cache)
        }
        
        save_cache(new_cache)
        logger.info(f"Successfully reloaded and cached {len(new_cache) - 1} Upstox instruments.")
        return new_cache
        
    except Exception as e:
        logger.error(f"Error reloading Upstox instrument master: {e}", exc_info=True)
        return {}

def get_upstox_instrument(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Looks up a symbol's instrument metadata (instrument_key, ISIN, Exchange, Trading Symbol).
    First checks index mappings, then local cache. Reloads master if symbol is missing or cache expired.
    """
    symbol_upper = symbol.upper().strip()
    
    # 1. Check Index Map
    if symbol_upper in INDEX_MAP:
        return INDEX_MAP[symbol_upper]
        
    # 2. Load Local Cache
    cache = load_cache()
    
    # 3. Check Cache Age (Reload if older than 24 hours)
    metadata = cache.get("_metadata", {})
    cache_time = metadata.get("timestamp", 0)
    current_time = time.time()
    
    cache_expired = (current_time - cache_time) > 86400 # 24 hours
    
    if not cache or cache_expired or symbol_upper not in cache:
        logger.info(f"Symbol {symbol_upper} not found in cache or cache expired. Reloading from Upstox master.")
        cache = reload_upstox_instrument_master()
        
    # 4. Lookup from Cache
    return cache.get(symbol_upper)
