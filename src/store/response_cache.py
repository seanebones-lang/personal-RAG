"""Simple in-memory response cache for query results."""

from __future__ import annotations

import hashlib
import json
import time
from functools import wraps
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
        # JSON-serialize with default=str so nested where filters hash stably
        payload = json.dumps({"q": query, **kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, query: str, **kwargs: Any) -> Optional[Any]:
        key = self._make_key(query, **kwargs)
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.ttl:
                self._hits += 1
                return val
            del self._cache[key]
        self._misses += 1
        return None

    def set(self, query: str, value: Any, **kwargs: Any) -> None:
        key = self._make_key(query, **kwargs)
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest = min(self._cache.items(), key=lambda x: x[1][0])[0]
            del self._cache[oldest]
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}


_response_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    global _response_cache
    if _response_cache is None:
        settings = get_settings()
        ttl = getattr(settings, "response_cache_ttl", 3600)
        max_size = getattr(settings, "response_cache_max_size", 1000)
        _response_cache = ResponseCache(ttl_seconds=ttl, max_size=max_size)
    return _response_cache


def reset_response_cache() -> None:
    """Clear singleton (after ingest/purge or in tests)."""
    global _response_cache
    if _response_cache is not None:
        _response_cache.clear()
    _response_cache = None


def cached_query(ttl: Optional[int] = None) -> Callable:
    """Decorator for caching query responses (optional helper)."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args: Any, **kwargs: Any) -> Any:
            cache = get_response_cache()
            if ttl is not None:
                cache.ttl = ttl
            filter_kw = {
                k: v
                for k, v in kwargs.items()
                if isinstance(v, (str, int, bool, float, type(None))) or v is None
            }
            hit = cache.get(query, **filter_kw)
            if hit is not None:
                return hit
            result = func(query, *args, **kwargs)
            cache.set(query, result, **filter_kw)
            return result

        return wrapper

    return decorator
