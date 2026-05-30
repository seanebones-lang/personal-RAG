import numpy as np

from src.retrieval.multi_query import expand_queries_heuristic, multi_query_search


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


def test_highlight_excerpt():
    from src.core.vault import highlight_excerpt

    text = "Hello world. The invoice total is fifty."
    out = highlight_excerpt(text, "invoice total is fifty")
    assert "**invoice total is fifty**" in out
