"""SQLite FTS5 sidecar for keyword search."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    try:
        for chunk_id, source, text in entries:
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
            conn.execute(
                "INSERT INTO chunks_fts (chunk_id, source, text) VALUES (?, ?, ?)",
                (chunk_id, source, text),
            )
        conn.commit()
    finally:
        conn.close()


def delete_by_sources(sources: List[str]) -> None:
    if not get_settings().use_fts:
        return
    conn = _connect()
    try:
        for source in sources:
            conn.execute("DELETE FROM chunks_fts WHERE source = ?", (source,))
        conn.commit()
    finally:
        conn.close()


def _sanitize_fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression (OR of tokens)."""
    tokens = re.findall(r"[A-Za-z0-9_]{2,}", query)
    if not tokens:
        # fallback: strip quotes/operators
        cleaned = re.sub(r'[^\w\s]', " ", query).strip()
        return cleaned if cleaned else query
    # OR-join keeps recall high for multi-word personal queries
    return " OR ".join(tokens[:24])


def search_fts(query: str, limit: int = 50) -> List[str]:
    """Return chunk_ids ranked by FTS5 relevance (bm25 lower is better)."""
    if not get_settings().use_fts:
        return []
    if not query or not str(query).strip():
        return []
    match = _sanitize_fts_query(query)
    conn = _connect()
    try:
        try:
            rows = conn.execute(
                """
                SELECT chunk_id FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts)
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Older SQLite without bm25() or bad MATCH — try plain MATCH
            try:
                rows = conn.execute(
                    """
                    SELECT chunk_id FROM chunks_fts
                    WHERE chunks_fts MATCH ?
                    LIMIT ?
                    """,
                    (match, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
    finally:
        conn.close()
    return [r[0] for r in rows]


def fetch_by_ids(chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """Hydrate FTS hits to {id, text, metadata} rows for hybrid merge."""
    if not chunk_ids or not get_settings().use_fts:
        return []
    conn = _connect()
    out: List[Dict[str, Any]] = []
    try:
        for cid in chunk_ids:
            row = conn.execute(
                "SELECT chunk_id, source, text FROM chunks_fts WHERE chunk_id = ? LIMIT 1",
                (cid,),
            ).fetchone()
            if not row:
                continue
            out.append(
                {
                    "id": row[0],
                    "text": row[2] or "",
                    "metadata": {"source": row[1] or ""},
                }
            )
    finally:
        conn.close()
    return out


def purge_fts() -> None:
    path = _db_path()
    if path.exists():
        path.unlink()


def reset_fts() -> None:
    purge_fts()
