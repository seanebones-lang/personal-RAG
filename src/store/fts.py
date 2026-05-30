"""SQLite FTS5 sidecar for keyword search."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple

from src.config import get_settings


def _db_path() -> Path:
    return get_settings().db_path.parent / "fts.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(chunk_id UNINDEXED, source UNINDEXED, text)
        """
    )
    conn.commit()
    return conn


def index_chunks(entries: List[Tuple[str, str, str]]) -> None:
    """entries: (chunk_id, source, text)"""
    if not get_settings().use_fts:
        return
    if not entries:
        return
    conn = _connect()
    for chunk_id, source, text in entries:
        conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
        conn.execute(
            "INSERT INTO chunks_fts (chunk_id, source, text) VALUES (?, ?, ?)",
            (chunk_id, source, text),
        )
    conn.commit()
    conn.close()


def delete_by_sources(sources: List[str]) -> None:
    if not get_settings().use_fts:
        return
    conn = _connect()
    for source in sources:
        conn.execute("DELETE FROM chunks_fts WHERE source = ?", (source,))
    conn.commit()
    conn.close()


def search_fts(query: str, limit: int = 50) -> List[str]:
    if not get_settings().use_fts:
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT chunk_id FROM chunks_fts
            WHERE chunks_fts MATCH ?
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [r[0] for r in rows]


def purge_fts() -> None:
    path = _db_path()
    if path.exists():
        path.unlink()


def reset_fts() -> None:
    purge_fts()
