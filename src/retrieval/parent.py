"""Parent-document expansion after chunk retrieval."""

from __future__ import annotations

from typing import Any, Dict, List, Set


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


def expand_parent_chunks(
    results: List[Dict[str, Any]],
    max_chars: int | None = None,
) -> List[Dict[str, Any]]:
    """Merge adjacent chunks from the same parent_id into wider context rows."""
    if not results:
        return []
    from src.config import get_settings
    from src.store.vectorstore import fetch_corpus

    settings = get_settings()
    limit = max_chars or settings.max_context_chars
    corpus = fetch_corpus(limit=100_000)
    by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for row in corpus:
        meta = row.get("metadata") or {}
        pid = str(meta.get("parent_id", ""))
        if pid:
            by_parent.setdefault(pid, []).append(row)

    for pid in by_parent:
        by_parent[pid].sort(
            key=lambda r: int((r.get("metadata") or {}).get("chunk_index", 0))
        )

    seen_parents: Set[str] = set()
    expanded: List[Dict[str, Any]] = []

    for hit in results:
        meta = hit.get("metadata") or {}
        pid = str(meta.get("parent_id", ""))
        if not pid or pid in seen_parents:
            expanded.append(hit)
            continue
        seen_parents.add(pid)
        siblings = by_parent.get(pid, [hit])
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
