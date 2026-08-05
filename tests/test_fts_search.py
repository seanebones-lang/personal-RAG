"""FTS sidecar search + hybrid wiring unit tests."""

from __future__ import annotations

from src.config import reset_settings
from src.store import fts


def test_search_fts_ranks_and_sanitizes(tmp_path, monkeypatch):
    monkeypatch.setenv("PRV_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("PRV_USE_FTS", "true")
    reset_settings()

    fts.index_chunks(
        [
            ("id1", "/a.md", "kalshi bitcoin market notes"),
            ("id2", "/b.md", "grocery list apples bananas"),
            ("id3", "/c.md", "bitcoin price action and streaks"),
        ]
    )
    hits = fts.search_fts("bitcoin market", limit=10)
    assert "id1" in hits or "id3" in hits
    # grocery should rank lower / may be absent depending on OR match
    assert hits[0] in {"id1", "id3"}

    hydrated = fts.fetch_by_ids(hits[:2])
    assert hydrated
    assert hydrated[0]["id"] in hits
    assert "text" in hydrated[0]


def test_search_fts_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("PRV_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("PRV_USE_FTS", "true")
    reset_settings()
    assert fts.search_fts("   ") == []
