"""Retrieval evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class EvalResult:
    question: str
    hit: bool
    reciprocal_rank: float
    expected: str


def _source_matches(metadata: Dict[str, Any], expected_substring: str) -> bool:
    source = str(metadata.get("source", ""))
    file_name = str(metadata.get("file_name", ""))
    needle = expected_substring.lower()
    return needle in source.lower() or needle in file_name.lower()


def score_retrieval(
    results: List[Dict[str, Any]],
    expected_source_contains: str,
    top_k: int,
) -> tuple[bool, float]:
    """Return (hit@k, reciprocal rank)."""
    for rank, row in enumerate(results[:top_k], start=1):
        meta = row.get("metadata") or {}
        if _source_matches(meta, expected_source_contains):
            return True, 1.0 / rank
    return False, 0.0


def aggregate(results: List[EvalResult]) -> Dict[str, float]:
    if not results:
        return {"hit_at_k": 0.0, "mrr": 0.0, "count": 0}
    hits = sum(1 for r in results if r.hit)
    mrr = sum(r.reciprocal_rank for r in results) / len(results)
    return {
        "hit_at_k": hits / len(results),
        "mrr": mrr,
        "count": float(len(results)),
    }
