import numpy as np

from src.retrieval.multi_query import expand_queries_heuristic, multi_query_search
from src.retrieval.presets import QUERY_PRESETS, resolve_query_preset


def test_expand_queries_heuristic():
    variants = expand_queries_heuristic("What is the invoice total for January?")
    assert variants[0].startswith("What")
    assert len(variants) >= 1


def test_multi_query_search_fusion():
    def search_fn(emb, k):
        q = float(emb[0])
        if q == 1.0:
            return [{"id": "a", "text": "a", "metadata": {}, "distance": 0.1}]
        return [{"id": "b", "text": "b", "metadata": {}, "distance": 0.2}]

    def embed_fn(q):
        return np.array([1.0] if "invoice" in q.lower() else [2.0])

    results = multi_query_search(
        ["invoice total", "total"],
        search_fn=search_fn,
        embed_fn=embed_fn,
        top_k=2,
    )
    assert len(results) >= 1
    ids = {r["id"] for r in results}
    assert "a" in ids or "b" in ids


def test_multi_query_with_hybrid_flag():
    """multi_query + hybrid should call hybrid_search path per variant."""
    calls = {"hybrid": 0}

    def search_fn(emb, k):
        return [{"id": "v", "text": "vec", "metadata": {}, "distance": 0.1}]

    def embed_fn(q):
        return np.array([0.5, 0.5])

    def vector_search_fn(emb, top_k=5, max_distance=None, where=None):
        return [{"id": "v", "text": "vec", "metadata": {}, "distance": 0.1}]

    def fetch_corpus_fn(where=None, limit=None):
        calls["hybrid"] += 1
        return [{"id": "k", "text": "key match invoice", "metadata": {}}]

    results = multi_query_search(
        ["invoice"],
        search_fn=search_fn,
        embed_fn=embed_fn,
        top_k=2,
        hybrid=True,
        vector_search_fn=vector_search_fn,
        fetch_corpus_fn=fetch_corpus_fn,
    )
    assert calls["hybrid"] >= 1
    assert len(results) >= 1


def test_highlight_excerpt():
    from src.core.vault import highlight_excerpt

    text = "Hello world. The invoice total is fifty."
    out = highlight_excerpt(text, "invoice total is fifty")
    assert "**invoice total is fifty**" in out


def test_query_presets_exist():
    assert set(QUERY_PRESETS) == {"fast", "balanced", "quality"}
    bal = resolve_query_preset("balanced")
    assert bal is not None
    assert bal.hybrid is True
    assert bal.rerank is True
    assert resolve_query_preset("nope") is None
