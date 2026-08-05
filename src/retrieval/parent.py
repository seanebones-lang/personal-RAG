"""Parent-document expansion after chunk retrieval."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


def _neighbor_window(
    siblings: List[Dict[str, Any]],
    center_index: int,
    max_chunks: int = 3,
) -> List[Dict[str, Any]]:
    if not siblings:
        return []
    by_idx = {
        int((s.get("metadata") or {}).get("chunk_index", i)): s
        for i, s in enumerate(siblings)
    }
    if center_index in by_idx:
        start = max(0, center_index - 1)
        end = center_index + 2
        window = [by_idx[i] for i in range(start, end) if i in by_idx]
        return window[:max_chunks]
    return siblings[:max_chunks]


def _siblings_for_parent(parent_id: str) -> List[Dict[str, Any]]:
    """Fetch sibling chunks by parent_id metadata (no full-corpus scan)."""
    from src.store.vectorstore import get_by_where

    try:
        rows = get_by_where({"parent_id": parent_id}, limit=500)
    except Exception as exc:
        logger.debug("parent expand get_by_where failed for %s: %s", parent_id, exc)
        return []
    rows.sort(key=lambda r: int((r.get("metadata") or {}).get("chunk_index", 0)))
    return rows


def expand_parent_chunks(
    results: List[Dict[str, Any]],
    max_chars: int | None = None,
) -> List[Dict[str, Any]]:
    """Merge adjacent chunks from the same parent_id into wider context rows."""
    if not results:
        return []
    from src.config import get_settings

    settings = get_settings()
    limit = max_chars or settings.max_context_chars

    seen_parents: Set[str] = set()
    expanded: List[Dict[str, Any]] = []
    sibling_cache: Dict[str, List[Dict[str, Any]]] = {}

    for hit in results:
        meta = hit.get("metadata") or {}
        pid = str(meta.get("parent_id", ""))
        if not pid or pid in seen_parents:
            expanded.append(hit)
            continue
        seen_parents.add(pid)

        if pid not in sibling_cache:
            sibling_cache[pid] = _siblings_for_parent(pid)
        siblings = sibling_cache[pid] or [hit]

        idx = int(meta.get("chunk_index", 0))
        window = _neighbor_window(siblings, idx, max_chunks=3)
        merged_text = "\n\n".join(s["text"] for s in window if s.get("text"))
        if len(merged_text) > limit:
            merged_text = merged_text[:limit] + "..."
        row = dict(hit)
        row["text"] = merged_text
        row["parent_expanded"] = True
        expanded.append(row)

    return expanded
