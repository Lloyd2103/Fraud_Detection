"""
Thread-safe In-Memory TTL Cache Module
Provides TTL cache wrappers for services and repositories.
"""
import time
import threading
from typing import Any, Optional, Dict, Tuple

class TTLCache:
    def __init__(self, default_ttl_seconds: float = 30.0):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[Any, Tuple[float, Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Optional[Any]:
        now = time.time()
        with self._lock:
            if key in self._cache:
                timestamp, value, ttl = self._cache[key]
                if now - timestamp < ttl:
                    return value
                else:
                    del self._cache[key]
        return None

    def set(self, key: Any, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        with self._lock:
            self._cache[key] = (time.time(), value, ttl)

    def delete(self, key: Any) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

