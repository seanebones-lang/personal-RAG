"""Hybrid retrieval: vector search + BM25 with reciprocal rank fusion."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from src.config import get_settings


def reciprocal_rank_fusion(
    ranked_lists: List[List[str]],
    k: int = 60,
) -> List[tuple[str, float]]:
    scores: Dict[str, float] = {}
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def bm25_rank(
    query: str,
    corpus: List[Dict[str, Any]],
    top_n: int,
) -> List[str]:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise RuntimeError(
            "Hybrid search requires rank-bm25. Install with: pip install rank-bm25"
        ) from exc

    if not corpus:
        return []
    tokenized = [doc["text"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    ids: List[str] = []
    for idx, _score in indexed[:top_n]:
        cid = corpus[idx].get("id")
        if cid:
            ids.append(cid)
    return ids


def merge_hybrid_results(
    vector_results: List[Dict[str, Any]],
    bm25_ids: List[str],
    corpus_by_id: Dict[str, Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    vector_ids = [r["id"] for r in vector_results if r.get("id")]
    fused = reciprocal_rank_fusion([vector_ids, bm25_ids])
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for doc_id, rrf_score in fused:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        if doc_id in {r.get("id") for r in vector_results}:
            row = next(r for r in vector_results if r.get("id") == doc_id)
            row = {**row, "rrf_score": rrf_score}
        elif doc_id in corpus_by_id:
            row = {
                **corpus_by_id[doc_id],
                "distance": 1.0,
                "rrf_score": rrf_score,
            }
        else:
            continue
        out.append(row)
        if len(out) >= top_k:
            break
    return out


def hybrid_search(
    query_text: str,
    query_embedding: np.ndarray,
    vector_search_fn,
    fetch_corpus_fn,
    top_k: int,
    where: Optional[Dict[str, Any]] = None,
    max_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    fetch_n = min(top_k * 4, settings.hybrid_fetch_limit)
    vector_results = vector_search_fn(
        query_embedding,
        top_k=fetch_n,
        max_distance=max_distance,
        where=where,
    )
    corpus = fetch_corpus_fn(where=where, limit=settings.hybrid_fetch_limit)
    corpus_by_id = {c["id"]: c for c in corpus if c.get("id")}

    for r in vector_results:
        r["id"] = r.get("id") or _id_from_metadata(r)

    bm25_ids = bm25_rank(query_text, corpus, top_n=fetch_n)
    return merge_hybrid_results(vector_results, bm25_ids, corpus_by_id, top_k)


def _id_from_metadata(row: Dict[str, Any]) -> str:
    meta = row.get("metadata") or {}
    source = meta.get("source", "")
    idx = meta.get("chunk_index", 0)
    return f"{source}::{idx}"
