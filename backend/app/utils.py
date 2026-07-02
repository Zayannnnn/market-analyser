import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class MemoryCache:
    """
    Lightweight, thread-safe in-memory cache to store API responses.
    Reduces compute latency and database read costs for serverless instances.
    """
    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                data, expiry = self._store[key]
                if time.time() < expiry:
                    logger.debug(f"MemoryCache HIT for key: {key}")
                    return data
                else:
                    logger.debug(f"MemoryCache EXPIRED for key: {key}")
                    del self._store[key]
            return None

    def set(self, key: str, value: Any, expiry_seconds: int = 900) -> None:
        with self._lock:
            self._store[key] = (value, time.time() + expiry_seconds)
            logger.debug(f"MemoryCache SET for key: {key} (Expiry: {expiry_seconds}s)")

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]
                logger.debug(f"MemoryCache INVALIDATED key: {key}")

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            logger.info("MemoryCache cleared.")

# Export global instance
api_cache = MemoryCache()
