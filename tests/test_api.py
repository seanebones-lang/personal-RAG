"""FastAPI layer smoke and unit tests."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.query.api import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "personalragvault"


def test_version():
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert isinstance(body["version"], str)
    assert len(body["version"]) > 0
    # Installed package or fallback should look like a semver-ish string
    assert body["version"][0].isdigit()


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


def test_query_mocked():
    fixed = {
        "results": [{"text": "hit", "source": "/tmp/a.md", "distance": 0.1}],
        "answer": "mocked answer",
        "context": "ctx",
        "llm_error": None,
        "timings": {"total_ms": 1.0},
        "cached": False,
    }
    client = TestClient(app)
    with patch("src.query.api.run_query", return_value=fixed) as mock_rq:
        r = client.post(
            "/query",
            json={"question": "what is this?", "use_llm": False, "top_k": 3},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "mocked answer"
    assert body["results"] == fixed["results"]
    assert body["timings"]["total_ms"] == 1.0
    assert body["cached"] is False
    mock_rq.assert_called_once()
    kwargs = mock_rq.call_args.kwargs
    assert kwargs["top_k"] == 3
    assert kwargs["use_llm"] is False
    assert kwargs["stream"] is False


def test_query_validation_error():
    client = TestClient(app)
    r = client.post("/query", json={})  # missing question
    assert r.status_code == 422
    r2 = client.post("/query", json={"question": "x", "top_k": 0})
    assert r2.status_code == 422


def test_ingest_dry_run_mocked():
    preview = {
        "path": "/tmp/docs",
        "files": 2,
        "chunks_estimate": 10,
        "dry_run": True,
    }
    client = TestClient(app)
    with patch("src.query.api.preview_ingest", return_value=preview) as mock_pi:
        r = client.post(
            "/ingest",
            json={
                "path": "/tmp/docs",
                "recursive": True,
                "dry_run": True,
                "allow_outside_home": True,
            },
        )
    assert r.status_code == 200
    assert r.json() == preview
    mock_pi.assert_called_once()
    args, kwargs = mock_pi.call_args
    assert kwargs.get("recursive") is True
    assert kwargs.get("allow_outside_home") is True


def test_auth_required(monkeypatch):
    """When PRV_API_TOKEN is set, protected routes need Bearer; public stay open."""
    monkeypatch.setenv("PRV_API_TOKEN", "secret-test-token")
    client = TestClient(app)

    # Public routes remain open
    assert client.get("/health").status_code == 200
    assert client.get("/version").status_code == 200

    # Protected without token
    r = client.get("/status")
    assert r.status_code == 401
    r2 = client.get("/cache/stats")
    assert r2.status_code == 401
    r3 = client.post("/query", json={"question": "hi", "use_llm": False})
    assert r3.status_code == 401

    # Wrong token
    bad = client.get(
        "/status",
        headers={"Authorization": "Bearer wrong"},
    )
    assert bad.status_code == 401

    # Correct token
    good = client.get(
        "/status",
        headers={"Authorization": "Bearer secret-test-token"},
    )
    assert good.status_code == 200
    assert "chunk_count" in good.json()

    # Empty token env disables auth again
    monkeypatch.setenv("PRV_API_TOKEN", "")
    open_r = client.get("/status")
    assert open_r.status_code == 200


def test_auth_unset_no_guard(monkeypatch):
    monkeypatch.delenv("PRV_API_TOKEN", raising=False)
    client = TestClient(app)
    assert client.get("/status").status_code == 200


def test_graph_neighbors_mocked():
    fixed = {
        "note": "Alpha",
        "outbound": ["Beta"],
        "inbound": [],
        "neighbors": ["Beta"],
        "notes_indexed": 2,
        "edges": 1,
    }
    client = TestClient(app)
    with patch("src.retrieval.graph.neighbors", return_value=fixed):
        r = client.get("/graph/neighbors", params={"note": "Alpha", "direction": "out"})
    assert r.status_code == 200
    assert r.json()["outbound"] == ["Beta"]


def test_graph_neighbors_bad_direction():
    client = TestClient(app)
    r = client.get("/graph/neighbors", params={"note": "X", "direction": "sideways"})
    assert r.status_code == 422
