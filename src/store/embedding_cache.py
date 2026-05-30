"""SQLite cache: chunk text hash -> embedding vector."""

from __future__ import annotations

import hashlib
import pickle
import sqlite3
from pathlib import Path
from typing import List, Optional

import numpy as np

from src.config import get_settings


def _db_path() -> Path:
    return get_settings().db_path.parent / "embedding_cache.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            chunk_id TEXT PRIMARY KEY,
            text_hash TEXT NOT NULL,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_cached(chunk_id: str, content_hash: str) -> Optional[np.ndarray]:
    if not get_settings().use_embedding_cache:
        return None
    conn = _connect()
    row = conn.execute(
        "SELECT vector FROM embeddings WHERE chunk_id = ? AND text_hash = ?",
        (chunk_id, content_hash),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return np.asarray(pickle.loads(row[0]))


def store_cached(chunk_id: str, content_hash: str, vector: np.ndarray) -> None:
    if not get_settings().use_embedding_cache:
        return
    conn = _connect()
    conn.execute(
        """
        INSERT INTO embeddings (chunk_id, text_hash, vector, dim)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chunk_id) DO UPDATE SET
            text_hash = excluded.text_hash,
            vector = excluded.vector,
            dim = excluded.dim
        """,
        (chunk_id, content_hash, pickle.dumps(vector), int(vector.shape[0])),
    )
    conn.commit()
    conn.close()


def delete_chunk_ids(chunk_ids: List[str]) -> None:
    if not get_settings().use_embedding_cache or not chunk_ids:
        return
    conn = _connect()
    for cid in chunk_ids:
        conn.execute("DELETE FROM embeddings WHERE chunk_id = ?", (cid,))
    conn.commit()
    conn.close()


def reset_cache() -> None:
    path = _db_path()
    if path.exists():
        path.unlink()
