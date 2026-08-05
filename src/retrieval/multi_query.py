"""Multi-query expansion and fusion."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from src.retrieval.hybrid import hybrid_search, reciprocal_rank_fusion

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "when",
        "where",
        "who",
        "how",
        "why",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "my",
        "me",
        "i",
    }
)


def expand_queries_heuristic(query: str, max_variants: int = 3) -> List[str]:
    """Generate query variants without LLM."""
    base = query.strip()
    if not base:
        return []
    variants: List[str] = [base]
    words = [w for w in re.findall(r"\w+", base.lower()) if w not in _STOPWORDS and len(w) > 2]
    if len(words) >= 2:
        keywords = " ".join(words[:8])
        if keywords.lower() != base.lower():
            variants.append(keywords)
    if len(words) >= 4:
        half = " ".join(words[len(words) // 2 :])
        if half:
            variants.append(half)
    # Light paraphrase-ish reorder for keyword queries
    if len(words) >= 3:
        reordered = " ".join(reversed(words[:6]))
        if reordered.lower() not in {v.lower() for v in variants}:
            variants.append(reordered)
    seen: set[str] = set()
    out: List[str] = []
    for v in variants:
        key = v.lower()
        if key not in seen:
            seen.add(key)
            out.append(v)
        if len(out) >= max_variants:
            break
    return out


def expand_queries_ollama(query: str) -> List[str]:
    """Ask Ollama for one alternate phrasing."""
    from src.ollama_client import generate_answer

    prompt = (
        "Rephrase this search query in one different way for document retrieval. "
        "Reply with only the rephrased query, one line.\n\n"
        f"Query: {query}"
    )
    alt = generate_answer(prompt).strip().splitlines()[0]
    if alt and alt.lower() != query.lower():
        return expand_queries_heuristic(query) + [alt]
    return expand_queries_heuristic(query)


def multi_query_search(
    queries: List[str],
    search_fn: Callable[[np.ndarray, int], List[Dict[str, Any]]],
    embed_fn: Callable[[str], np.ndarray],
    top_k: int,
    rrf_k: int = 60,
    hybrid: bool = False,
    vector_search_fn=None,
    fetch_corpus_fn=None,
    where: Optional[Dict[str, Any]] = None,
    max_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Run search per query variant and fuse with RRF.

    When ``hybrid=True``, each variant uses hybrid_search (vector + FTS/BM25).
    Otherwise uses pure vector ``search_fn(embedding, k)``.
    """
    ranked_lists: List[List[str]] = []
    by_id: Dict[str, Dict[str, Any]] = {}

    fetch_k = max(top_k * 3, 20)
    for q in queries:
        if hybrid and vector_search_fn is not None and fetch_corpus_fn is not None:
            emb = embed_fn(q)
            hits = hybrid_search(
                query_text=q,
                query_embedding=emb,
                vector_search_fn=vector_search_fn,
                fetch_corpus_fn=fetch_corpus_fn,
                top_k=fetch_k,
                where=where,
                max_distance=max_distance,
            )
        else:
            emb = embed_fn(q)
            hits = search_fn(emb, fetch_k)
        ids: List[str] = []
        for row in hits:
            cid = row.get("id")
            if cid:
                ids.append(cid)
                by_id[cid] = row
        if ids:
            ranked_lists.append(ids)

    if not ranked_lists:
        return []

    fused = reciprocal_rank_fusion(ranked_lists, k=rrf_k)
    out: List[Dict[str, Any]] = []
    for doc_id, score in fused[:top_k]:
        row = dict(by_id[doc_id])
        row["rrf_score"] = score
        out.append(row)
    return out
