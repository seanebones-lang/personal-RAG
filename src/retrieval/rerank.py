"""Cross-encoder reranking (optional [retrieval] extra)."""

from __future__ import annotations

from typing import Any, Dict, List


def rerank_results(
    query: str,
    results: List[Dict[str, Any]],
    top_k: int,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> List[Dict[str, Any]]:
    """Rerank candidates with a cross-encoder; requires sentence-transformers."""
    if not results:
        return []
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Reranking requires sentence-transformers. "
            "Install with: pip install personalragvault[retrieval]"
        ) from exc

    model = CrossEncoder(model_name)
    pairs = [(query, r.get("text", "")) for r in results]
    scores = model.predict(pairs)
    scored = list(zip(results, scores))
    scored.sort(key=lambda x: float(x[1]), reverse=True)
    out: List[Dict[str, Any]] = []
    for row, score in scored[:top_k]:
        item = dict(row)
        item["rerank_score"] = float(score)
        out.append(item)
    return out
