"""Cross-encoder reranking (optional [retrieval] extra)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.retrieval.reranker_presets import resolve_reranker_model

logger = logging.getLogger(__name__)

_reranker = None
_reranker_name: Optional[str] = None


def reset_reranker() -> None:
    """Clear cached cross-encoder (for tests / model switches)."""
    global _reranker, _reranker_name
    _reranker = None
    _reranker_name = None


def get_reranker(model_name: str):
    """Process-level CrossEncoder singleton (avoids reload every query)."""
    global _reranker, _reranker_name
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Reranking requires sentence-transformers. "
            "Reinstall the base package from your source checkout or release wheel. See INSTALL.md."
        ) from exc

    resolved = resolve_reranker_model(model_name)
    if _reranker is None or _reranker_name != resolved:
        logger.info("Loading cross-encoder reranker: %s", resolved)
        _reranker = CrossEncoder(resolved)
        _reranker_name = resolved
    return _reranker


def rerank_results(
    query: str,
    results: List[Dict[str, Any]],
    top_k: int,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> List[Dict[str, Any]]:
    """Rerank candidates with a cross-encoder; requires sentence-transformers.

    Preserves prior ``rrf_score`` / ``distance`` on each row and adds ``rerank_score``.
    """
    if not results:
        return []

    model = get_reranker(model_name)
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
