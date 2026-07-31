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


def precision_at_k(results: List[Dict[str, Any]], expected_source_contains: str, k: int) -> float:
    """Precision@k: fraction of top-k results that are relevant."""
    if not results or k <= 0:
        return 0.0
    rels = relevance_scores(results, expected_source_contains, k)
    relevant = sum(1 for s in rels if s > 0)
    return relevant / len(rels)

def average_precision(results: List[Dict[str, Any]], expected_source_contains: str, k: int) -> float:
    """AP@k approximation for single relevant (simplified MAP when 1 relevant)."""
    rels = relevance_scores(results, expected_source_contains, k)
    if not any(rels):
        return 0.0
    precisions = []
    num_relevant = 0
    for i, rel in enumerate(rels, 1):
        if rel > 0:
            num_relevant += 1
            precisions.append(num_relevant / i)
    return sum(precisions) / num_relevant if precisions else 0.0

def context_relevance(results: List[Dict[str, Any]], query: str, k: int = 3) -> float:
    """Simple heuristic context relevance: overlap of query terms in top results."""
    if not results:
        return 0.0
    query_terms = set(query.lower().split())
    scores = []
    for row in results[:k]:
        text = (row.get("text", "") + " " + str(row.get("metadata", {}))).lower()
        overlap = len(query_terms & set(text.split())) / max(1, len(query_terms))
        scores.append(overlap)
    return sum(scores) / len(scores) if scores else 0.0

def aggregate(results: List[EvalResult]) -> Dict[str, float]:
    if not results:
        return {"hit_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0, "precision_at_k": 0.0, "map": 0.0, "count": 0}
    n = len(results)
    hits = sum(1 for r in results if r.hit)
    mrr = sum(r.reciprocal_rank for r in results) / n
    ndcg = sum(r.ndcg for r in results) / n
    # Note: precision/map require per-case recalc; placeholder avg from hits
    prec = hits / n  # approx using hit rate
    return {
        "hit_at_k": hits / n,
        "mrr": mrr,
        "ndcg_at_k": ndcg,
        "precision_at_k": prec,
        "map": mrr,  # approx
        "count": float(n),
    }
