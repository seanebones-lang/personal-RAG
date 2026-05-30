"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.config import reset_settings
from src.embed.embedder import reset_model
from src.store.vectorstore import reset_client


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Isolate DB path and reset singletons per test."""
    db_path = tmp_path / "chroma"
    monkeypatch.setenv("PRV_DB_PATH", str(db_path))
    monkeypatch.setenv("PRV_CHUNK_SIZE", "100")
    monkeypatch.setenv("PRV_CHUNK_OVERLAP", "20")
    reset_settings()
    reset_client()
    reset_model()
    yield
    reset_settings()
    reset_client()
    reset_model()
