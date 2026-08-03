"""Lightweight Obsidian wikilink graph over vault metadata (no separate graph DB)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.store.vectorstore import fetch_corpus


def _note_key_from_source(source: str) -> str:
    """Derive a note name comparable to wikilink targets."""
    # strip #docN multi-doc suffix from pipeline
    base = source.split("#doc", 1)[0]
    p = Path(base)
    return p.stem


def _parse_wikilinks(meta: Dict[str, Any]) -> List[str]:
    raw = meta.get("wikilinks")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def build_wikilink_adjacency(
    limit: Optional[int] = None,
) -> Tuple[Dict[str, Set[str]], Dict[str, str]]:
    """Return (note -> outbound targets, note -> sample source path)."""
    corpus = fetch_corpus(limit=limit)
    adj: Dict[str, Set[str]] = defaultdict(set)
    sources: Dict[str, str] = {}

    for row in corpus:
        meta = row.get("metadata") or {}
        source = str(meta.get("source") or row.get("source") or "")
        if not source:
            continue
        note = _note_key_from_source(source)
        sources.setdefault(note, source)
        for target in _parse_wikilinks(meta):
            # normalize targets like folder/Note
            t = Path(target).stem if "/" in target or "\\" in target else target
            t = t.strip()
            if t and t != note:
                adj[note].add(t)

    return dict(adj), sources


def neighbors(
    note: str,
    *,
    direction: str = "out",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Neighbors for a note name (stem) using wikilink metadata.

    direction: out | in | both
    """
    note = note.strip()
    if note.endswith(".md"):
        note = note[:-3]
    adj, sources = build_wikilink_adjacency(limit=limit)

    out_links = sorted(adj.get(note, set()))
    inbound: List[str] = []
    for src, targets in adj.items():
        if note in targets:
            inbound.append(src)
    inbound = sorted(set(inbound))

    if direction == "out":
        linked = out_links
    elif direction == "in":
        linked = inbound
    else:
        linked = sorted(set(out_links) | set(inbound))

    return {
        "note": note,
        "source": sources.get(note),
        "direction": direction,
        "outbound": out_links,
        "inbound": inbound,
        "neighbors": linked,
        "notes_indexed": len(sources),
        "edges": sum(len(v) for v in adj.values()),
    }


def export_edges(limit: Optional[int] = None) -> List[Dict[str, str]]:
    """Flat edge list {from, to} for JSON export."""
    adj, _ = build_wikilink_adjacency(limit=limit)
    edges: List[Dict[str, str]] = []
    for src, targets in sorted(adj.items()):
        for t in sorted(targets):
            edges.append({"from": src, "to": t})
    return edges


def export_edges_json(path: Path, limit: Optional[int] = None) -> int:
    edges = export_edges(limit=limit)
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"edges": edges, "count": len(edges)}, indent=2), encoding="utf-8")
    return len(edges)
