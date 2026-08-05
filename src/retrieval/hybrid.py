"""Hybrid retrieval: vector + FTS5/BM25 with reciprocal rank fusion."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import get_settings

logger = logging.getLogger(__name__)


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
    keyword_ids: List[str],
    corpus_by_id: Dict[str, Dict[str, Any]],
    top_k: int,
    rrf_k: int = 60,
) -> List[Dict[str, Any]]:
    """Fuse vector-ranked ids with keyword-ranked ids via RRF."""
    vector_ids = [r["id"] for r in vector_results if r.get("id")]
    fused = reciprocal_rank_fusion([vector_ids, keyword_ids], k=rrf_k)
    vector_by_id = {r.get("id"): r for r in vector_results if r.get("id")}
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for doc_id, rrf_score in fused:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        if doc_id in vector_by_id:
            row = {**vector_by_id[doc_id], "rrf_score": rrf_score}
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


def _keyword_rank_ids(
    query_text: str,
    top_n: int,
    where: Optional[Dict[str, Any]],
    fetch_corpus_fn,
    settings,
) -> tuple[List[str], Dict[str, Dict[str, Any]]]:
    """Prefer FTS5 sidecar; fall back to in-memory BM25 over a capped corpus."""
    corpus_by_id: Dict[str, Dict[str, Any]] = {}
    keyword_ids: List[str] = []

    if settings.use_fts:
        try:
            from src.store.fts import fetch_by_ids, search_fts

            fts_ids = search_fts(query_text, limit=top_n)
            if fts_ids:
                keyword_ids = fts_ids
                # Hydrate rows missing from vector results later via corpus map
                for row in fetch_by_ids(fts_ids):
                    if row.get("id"):
                        corpus_by_id[row["id"]] = row
                return keyword_ids, corpus_by_id
        except Exception as exc:
            logger.debug("FTS keyword path failed, falling back to BM25: %s", exc)

    # BM25 fallback — capped fetch (never full vault)
    corpus = fetch_corpus_fn(where=where, limit=min(settings.hybrid_fetch_limit, top_n * 20))
    corpus_by_id = {c["id"]: c for c in corpus if c.get("id")}
    keyword_ids = bm25_rank(query_text, corpus, top_n=top_n)
    return keyword_ids, corpus_by_id


def hybrid_search(
    query_text: str,
    query_embedding: np.ndarray,
    vector_search_fn,
    fetch_corpus_fn,
    top_k: int,
    where: Optional[Dict[str, Any]] = None,
    max_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Vector + keyword (FTS5 preferred, BM25 fallback) fused with RRF."""
    settings = get_settings()
    fetch_n = min(max(top_k * 4, 20), settings.hybrid_fetch_limit)
    vector_results = vector_search_fn(
        query_embedding,
        top_k=fetch_n,
        max_distance=max_distance,
        where=where,
    )
    for r in vector_results:
        r["id"] = r.get("id") or _id_from_metadata(r)

    keyword_ids, corpus_by_id = _keyword_rank_ids(
        query_text,
        top_n=fetch_n,
        where=where,
        fetch_corpus_fn=fetch_corpus_fn,
        settings=settings,
    )

    # Ensure vector hits are available for merge even if not in FTS hydrate set
    for r in vector_results:
        rid = r.get("id")
        if rid and rid not in corpus_by_id:
            corpus_by_id[rid] = r

    return merge_hybrid_results(
        vector_results,
        keyword_ids,
        corpus_by_id,
        top_k,
        rrf_k=settings.hybrid_rrf_k,
    )


def _id_from_metadata(row: Dict[str, Any]) -> str:
    meta = row.get("metadata") or {}
    source = meta.get("source", "")
    idx = meta.get("chunk_index", 0)
    return f"{source}::{idx}"
