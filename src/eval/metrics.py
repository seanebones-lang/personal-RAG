"""Retrieval evaluation metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class EvalResult:
    question: str
    hit: bool
    reciprocal_rank: float
    ndcg: float
    expected: str


def _source_matches(metadata: Dict[str, Any], expected_substring: str) -> bool:
    source = str(metadata.get("source", ""))
    file_name = str(metadata.get("file_name", ""))
    needle = expected_substring.lower()
    return needle in source.lower() or needle in file_name.lower()


def relevance_scores(
    results: List[Dict[str, Any]],
    expected_source_contains: str,
    top_k: int,
) -> List[float]:
    """Binary relevance per rank (1.0 if source matches, else 0.0)."""
    scores: List[float] = []
    for row in results[:top_k]:
        meta = row.get("metadata") or {}
        scores.append(1.0 if _source_matches(meta, expected_source_contains) else 0.0)
    return scores


def dcg_at_k(relevances: List[float], k: int) -> float:
    total = 0.0
    for i, rel in enumerate(relevances[:k]):
        if rel <= 0:
            continue
        total += rel / math.log2(i + 2)
    return total


def ndcg_at_k(
    results: List[Dict[str, Any]],
    expected_source_contains: str,
    k: int,
) -> float:
    """NDCG@k with binary relevance from expected_source_contains."""
    rels = relevance_scores(results, expected_source_contains, k)
    if not rels or max(rels) == 0:
        return 0.0
    dcg = dcg_at_k(rels, k)
    ideal = sorted(rels, reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def score_retrieval(
    results: List[Dict[str, Any]],
    expected_source_contains: str,
    top_k: int,
) -> tuple[bool, float, float]:
    """Return (hit@k, reciprocal rank, ndcg@k)."""
    rels = relevance_scores(results, expected_source_contains, top_k)
    ndcg = ndcg_at_k(results, expected_source_contains, top_k)
    for rank, rel in enumerate(rels, start=1):
        if rel > 0:
            return True, 1.0 / rank, ndcg
    return False, 0.0, ndcg


def aggregate(results: List[EvalResult]) -> Dict[str, float]:
    if not results:
        return {"hit_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0, "count": 0}
    n = len(results)
    hits = sum(1 for r in results if r.hit)
    mrr = sum(r.reciprocal_rank for r in results) / n
    ndcg = sum(r.ndcg for r in results) / n
    return {
        "hit_at_k": hits / n,
        "mrr": mrr,
        "ndcg_at_k": ndcg,
        "count": float(n),
    }
