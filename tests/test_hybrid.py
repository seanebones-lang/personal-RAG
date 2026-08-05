from src.retrieval.hybrid import merge_hybrid_results, reciprocal_rank_fusion


def test_rrf_merges_lists():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    ids = [x[0] for x in fused]
    assert "b" in ids
    assert ids[0] == "b"


def test_merge_hybrid_prefers_fused_order():
    vector = [
        {"id": "a", "text": "alpha", "metadata": {}, "distance": 0.1},
        {"id": "b", "text": "beta", "metadata": {}, "distance": 0.2},
    ]
    keyword_ids = ["b", "c"]
    corpus = {
        "c": {"id": "c", "text": "gamma", "metadata": {"source": "c.txt"}},
    }
    out = merge_hybrid_results(vector, keyword_ids, corpus, top_k=3)
    ids = [r["id"] for r in out]
    assert "b" in ids
    assert all("rrf_score" in r for r in out)
