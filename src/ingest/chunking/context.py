"""Per-run chunk strategy override (ingest CLI / UI)."""

from __future__ import annotations

import contextvars

_chunk_strategy_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "chunk_strategy_override", default=None
)


def set_chunk_strategy_override(strategy: str | None) -> contextvars.Token:
    return _chunk_strategy_override.set(strategy)


def reset_chunk_strategy_override(token: contextvars.Token) -> None:
    _chunk_strategy_override.reset(token)


def get_chunk_strategy_override() -> str | None:
    return _chunk_strategy_override.get()
