"""Simple in-memory + optional disk response cache for query results."""
from __future__ import annotations

import hashlib
import json
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from src.config import get_settings


class ResponseCache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, **kwargs: Any) -> str:
        payload = json.dumps({"q": query, **kwargs}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, query: str, **kwargs: Any) -> Optional[Any]:
        key = self._make_key(query, **kwargs)
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.ttl:
                self._hits += 1
                return val
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def set(self, query: str, value: Any, **kwargs: Any) -> None:
        key = self._make_key(query, **kwargs)
        if len(self._cache) >= self.max_size:
            # simple eviction
            oldest = min(self._cache.items(), key=lambda x: x[1][0])[0]
            del self._cache[oldest]
        self._cache[key] = (time.time(), value)

    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}


_response_cache = None


def get_response_cache() -> ResponseCache:
    global _response_cache
    if _response_cache is None:
        settings = get_settings()
        ttl = getattr(settings, "response_cache_ttl", 3600)
        _response_cache = ResponseCache(ttl_seconds=ttl)
    return _response_cache


def cached_query(ttl: Optional[int] = None):
    """Decorator for caching query responses."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args, **kwargs):
            cache = get_response_cache()
            cached = cache.get(query, **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, bool, float))})
            if cached is not None:
                return cached
            result = func(query, *args, **kwargs)
            cache.set(query, result, **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, bool, float))})
            return result

        return wrapper

    return decorator
