"""Opinionated query quality presets: fast / balanced / quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class QueryPreset:
    name: str
    hybrid: bool
    multi_query: bool
    expand_query: bool
    rerank: bool
    parent_expand: bool
    description: str


QUERY_PRESETS: Dict[str, QueryPreset] = {
    "fast": QueryPreset(
        name="fast",
        hybrid=False,
        multi_query=False,
        expand_query=False,
        rerank=False,
        parent_expand=False,
        description="Vector-only retrieval; lowest latency.",
    ),
    "balanced": QueryPreset(
        name="balanced",
        hybrid=True,
        multi_query=False,
        expand_query=False,
        rerank=True,
        parent_expand=False,
        description="Hybrid (vector+FTS/BM25) + cross-encoder rerank.",
    ),
    "quality": QueryPreset(
        name="quality",
        hybrid=True,
        multi_query=True,
        expand_query=False,
        rerank=True,
        parent_expand=True,
        description="Hybrid + multi-query fusion + rerank + parent expand.",
    ),
}


def resolve_query_preset(name: Optional[str]) -> Optional[QueryPreset]:
    if not name:
        return None
    key = str(name).strip().lower()
    return QUERY_PRESETS.get(key)


def list_query_presets() -> list[dict]:
    return [
        {
            "name": p.name,
            "hybrid": p.hybrid,
            "multi_query": p.multi_query,
            "expand_query": p.expand_query,
            "rerank": p.rerank,
            "parent_expand": p.parent_expand,
            "description": p.description,
        }
        for p in QUERY_PRESETS.values()
    ]
