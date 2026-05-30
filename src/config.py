"""Configuration from environment variables with validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _expand_path(value: str) -> Path:
    return Path(os.path.expanduser(value)).resolve()


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if val < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {val}")
    return val


@dataclass(frozen=True)
class Settings:
    db_path: Path
    embed_model: str
    ollama_host: str
    ollama_model: str
    max_file_bytes: int
    chunk_size: int
    chunk_overlap: int
    max_context_chars: int
    max_top_k: int
    collection_name: str = "personal_knowledge"

    @classmethod
    def from_env(cls) -> Settings:
        chunk_size = _int_env("PRV_CHUNK_SIZE", 800, minimum=100)
        chunk_overlap = _int_env("PRV_CHUNK_OVERLAP", 120, minimum=0)
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"PRV_CHUNK_OVERLAP ({chunk_overlap}) must be less than "
                f"PRV_CHUNK_SIZE ({chunk_size})"
            )
        return cls(
            db_path=_expand_path(os.environ.get("PRV_DB_PATH", "~/.personalragvault/chroma")),
            embed_model=os.environ.get("PRV_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            ollama_host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            max_file_bytes=_int_env("PRV_MAX_FILE_BYTES", 52_428_800, minimum=1),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_context_chars=_int_env("PRV_MAX_CONTEXT_CHARS", 12_000, minimum=500),
            max_top_k=_int_env("PRV_MAX_TOP_K", 50, minimum=1),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (for tests)."""
    global _settings
    _settings = None
