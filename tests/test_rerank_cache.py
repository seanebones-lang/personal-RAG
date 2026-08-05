from src.retrieval import rerank as rerank_mod


def test_reset_reranker_clears_singleton():
    rerank_mod._reranker = object()
    rerank_mod._reranker_name = "x"
    rerank_mod.reset_reranker()
    assert rerank_mod._reranker is None
    assert rerank_mod._reranker_name is None
