import pytest

from src.config import (
    DEFAULT_INGEST_EXCLUDE_DIRS,
    Settings,
    get_settings,
    reset_settings,
)


def test_chunk_overlap_validation(monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_SIZE", "100")
    monkeypatch.setenv("PRV_CHUNK_OVERLAP", "100")
    reset_settings()
    with pytest.raises(ValueError, match="PRV_CHUNK_OVERLAP"):
        Settings.from_env()


def test_hybrid_default_false_by_default(monkeypatch):
    monkeypatch.delenv("PRV_HYBRID", raising=False)
    reset_settings()
    s = Settings.from_env()
    assert s.hybrid_default is False
    assert get_settings().hybrid_default is False


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("", False),
    ],
)
def test_hybrid_default_from_prv_hybrid(monkeypatch, raw, expected):
    monkeypatch.setenv("PRV_HYBRID", raw)
    reset_settings()
    assert Settings.from_env().hybrid_default is expected


def test_ingest_exclude_dirs_defaults(monkeypatch):
    monkeypatch.delenv("PRV_INGEST_EXCLUDE_DIRS", raising=False)
    reset_settings()
    s = Settings.from_env()
    assert s.ingest_exclude_dirs == DEFAULT_INGEST_EXCLUDE_DIRS
    for name in (".obsidian", ".git", "node_modules", "__pycache__"):
        assert name in s.ingest_exclude_dirs


def test_ingest_exclude_dirs_extra_from_env(monkeypatch):
    monkeypatch.setenv("PRV_INGEST_EXCLUDE_DIRS", " drafts , tmp_build ")
    reset_settings()
    s = Settings.from_env()
    assert "drafts" in s.ingest_exclude_dirs
    assert "tmp_build" in s.ingest_exclude_dirs
    assert ".obsidian" in s.ingest_exclude_dirs


def test_query_preset_from_env(monkeypatch):
    monkeypatch.setenv("PRV_QUERY_PRESET", "Balanced")
    reset_settings()
    assert Settings.from_env().query_preset == "balanced"
    monkeypatch.delenv("PRV_QUERY_PRESET", raising=False)
    reset_settings()
    assert Settings.from_env().query_preset is None
