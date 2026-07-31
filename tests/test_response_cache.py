"""Tests for response cache."""

from src.store.response_cache import ResponseCache, get_response_cache, reset_response_cache


def test_response_cache_hit_miss():
    c = ResponseCache(ttl_seconds=60, max_size=10)
    assert c.get("q", top_k=5) is None
    c.set("q", {"answer": "a"}, top_k=5)
    assert c.get("q", top_k=5) == {"answer": "a"}
    assert c.get("q", top_k=3) is None  # different kwargs
    stats = c.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["size"] == 1


def test_response_cache_ttl_expiry(monkeypatch):
    c = ResponseCache(ttl_seconds=10, max_size=10)
    c.set("q", 1)
    # force expire
    key = next(iter(c._cache))
    ts, val = c._cache[key]
    c._cache[key] = (ts - 100, val)
    assert c.get("q") is None


def test_response_cache_eviction():
    c = ResponseCache(ttl_seconds=60, max_size=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    assert c.stats()["size"] == 2
    assert c.get("c") == 3


def test_get_response_cache_singleton(monkeypatch):
    monkeypatch.setenv("PRV_RESPONSE_CACHE_TTL", "120")
    reset_response_cache()
    a = get_response_cache()
    b = get_response_cache()
    assert a is b
    reset_response_cache()
