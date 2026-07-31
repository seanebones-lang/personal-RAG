"""FastAPI layer smoke tests."""

from fastapi.testclient import TestClient

from src.query.api import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_status_endpoint():
    client = TestClient(app)
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert "chunk_count" in body
    assert "db_path" in body


def test_cache_stats_and_clear():
    client = TestClient(app)
    r = client.get("/cache/stats")
    assert r.status_code == 200
    assert "hits" in r.json()
    r2 = client.post("/cache/clear")
    assert r2.status_code == 200
    assert r2.json()["status"] == "cleared"
