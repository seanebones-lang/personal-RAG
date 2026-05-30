import pytest

from src.config import Settings, reset_settings


def test_chunk_overlap_validation(monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_SIZE", "100")
    monkeypatch.setenv("PRV_CHUNK_OVERLAP", "100")
    reset_settings()
    with pytest.raises(ValueError, match="PRV_CHUNK_OVERLAP"):
        Settings.from_env()
