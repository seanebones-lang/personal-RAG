"""Configuration from environment variables with validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.embed.presets import resolve_embed_model

CHUNK_STRATEGIES = frozenset({"char", "recursive", "semantic"})


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


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    db_path: Path
    embed_model: str
    embed_preset: str | None
    ollama_host: str
    ollama_model: str
    max_file_bytes: int
    chunk_size: int
    chunk_overlap: int
    chunk_strategy: str
    chunk_min_size: int
    chunk_max_size: int
    max_context_chars: int
    max_top_k: int
    embed_batch_size: int
    use_file_cache: bool
    use_fts: bool
    use_embedding_cache: bool
    hybrid_fetch_limit: int
    hybrid_rrf_k: int
    hnsw_search_ef: int
    hnsw_m: int
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
        chunk_min = _int_env("PRV_CHUNK_MIN_SIZE", 200, minimum=50)
        chunk_max = _int_env("PRV_CHUNK_MAX_SIZE", chunk_size, minimum=chunk_min)
        strategy = os.environ.get("PRV_CHUNK_STRATEGY", "char").strip().lower()
        if strategy not in CHUNK_STRATEGIES:
            raise ValueError(
                f"PRV_CHUNK_STRATEGY must be one of {sorted(CHUNK_STRATEGIES)}, got {strategy!r}"
            )

        preset = os.environ.get("PRV_EMBED_PRESET")
        explicit_model = os.environ.get("PRV_EMBED_MODEL")
        if preset:
            embed_model = resolve_embed_model(preset)
        elif explicit_model:
            embed_model = explicit_model
        else:
            embed_model = resolve_embed_model("mini")

        return cls(
            db_path=_expand_path(
                os.environ.get("PRV_DB_PATH", "~/.personalragvault/chroma")
            ),
            embed_model=embed_model,
            embed_preset=preset,
            ollama_host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            max_file_bytes=_int_env("PRV_MAX_FILE_BYTES", 52_428_800, minimum=1),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_strategy=strategy,
            chunk_min_size=chunk_min,
            chunk_max_size=chunk_max,
            max_context_chars=_int_env("PRV_MAX_CONTEXT_CHARS", 12_000, minimum=500),
            max_top_k=_int_env("PRV_MAX_TOP_K", 50, minimum=1),
            embed_batch_size=_int_env("PRV_EMBED_BATCH_SIZE", 32, minimum=1),
            use_file_cache=_bool_env("PRV_USE_FILE_CACHE", True),
            use_fts=_bool_env("PRV_USE_FTS", True),
            use_embedding_cache=_bool_env("PRV_USE_EMBEDDING_CACHE", True),
            hybrid_fetch_limit=_int_env("PRV_HYBRID_FETCH_LIMIT", 5000, minimum=100),
            hybrid_rrf_k=_int_env("PRV_HYBRID_RRF_K", 60, minimum=1),
            hnsw_search_ef=_int_env("PRV_HNSW_SEARCH_EF", 100, minimum=10),
            hnsw_m=_int_env("PRV_HNSW_M", 16, minimum=4),
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
