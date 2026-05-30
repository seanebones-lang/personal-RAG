from src.retrieval.hybrid import reciprocal_rank_fusion


def test_rrf_merges_lists():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    ids = [x[0] for x in fused]
    assert "b" in ids
    assert ids[0] == "b"
