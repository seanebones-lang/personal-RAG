"""SQLite sidecar: skip unchanged files on re-ingest."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from src.config import get_settings


def _db_path() -> Path:
    return get_settings().db_path.parent / "file_cache.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_hashes (
            source TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            mtime INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def file_content_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def should_skip_file(file_path: Path, force: bool = False) -> bool:
    if force:
        return False
    if not get_settings().use_file_cache:
        return False
    source = str(file_path.resolve())
    try:
        stat = file_path.stat()
        content_hash = file_content_hash(file_path)
    except OSError:
        return False

    conn = _connect()
    row = conn.execute(
        "SELECT content_hash, mtime FROM file_hashes WHERE source = ?",
        (source,),
    ).fetchone()
    conn.close()
    if row and row[0] == content_hash and row[1] == int(stat.st_mtime):
        return True
    return False


def record_file(file_path: Path) -> None:
    if not get_settings().use_file_cache:
        return
    source = str(file_path.resolve())
    stat = file_path.stat()
    content_hash = file_content_hash(file_path)
    import time

    conn = _connect()
    conn.execute(
        """
        INSERT INTO file_hashes (source, content_hash, mtime, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            content_hash = excluded.content_hash,
            mtime = excluded.mtime,
            updated_at = excluded.updated_at
        """,
        (source, content_hash, int(stat.st_mtime), int(time.time())),
    )
    conn.commit()
    conn.close()


def remove_sources(sources: list[str]) -> None:
    if not get_settings().use_file_cache:
        return
    conn = _connect()
    for source in sources:
        conn.execute("DELETE FROM file_hashes WHERE source = ?", (source,))
    conn.commit()
    conn.close()


def compact_orphans(valid_sources: set[str]) -> int:
    conn = _connect()
    rows = conn.execute("SELECT source FROM file_hashes").fetchall()
    removed = 0
    for (source,) in rows:
        if source not in valid_sources:
            conn.execute("DELETE FROM file_hashes WHERE source = ?", (source,))
            removed += 1
    conn.commit()
    conn.close()
    return removed


def reset_cache() -> None:
    path = _db_path()
    if path.exists():
        path.unlink()
