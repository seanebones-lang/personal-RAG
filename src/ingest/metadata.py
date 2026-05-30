"""Build Chroma-compatible metadata for chunks."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _chroma_meta(data: Dict[str, Any]) -> Dict[str, str | int | float | bool]:
    """Keep only types Chroma accepts."""
    out: Dict[str, str | int | float | bool] = {}
    for key, val in data.items():
        if val is None:
            continue
        if isinstance(val, (str, int, float, bool)):
            out[key] = val
        elif isinstance(val, (list, dict)):
            out[key] = str(val)[:500]
        else:
            out[key] = str(val)[:500]
    return out


def build_chunk_metadata(
    file_path: Path,
    ingest_root: Path,
    chunk_index: int,
    total_chunks: int,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, str | int | float | bool]:
    resolved = file_path.resolve()
    stat = resolved.stat()
    mtime = int(stat.st_mtime)
    year = datetime.fromtimestamp(mtime, tz=timezone.utc).year

    try:
        relative = str(resolved.relative_to(ingest_root.resolve()))
    except ValueError:
        relative = resolved.name

    meta: Dict[str, Any] = {
        "source": str(resolved),
        "file_name": resolved.name,
        "extension": resolved.suffix.lower(),
        "mtime": mtime,
        "year": year,
        "ingested_at": int(time.time()),
        "relative_path": relative,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
    }
    if extra:
        meta.update(extra)
    return _chroma_meta(meta)
