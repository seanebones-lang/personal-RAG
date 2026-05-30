import numpy as np

from src.store.vectorstore import count_documents, purge_collection, search, upsert_documents


def _fake_embedding(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(384, dtype=np.float32)


def test_upsert_and_search():
    docs = [
        {
            "id": "doc1",
            "text": "RAG systems use retrieval",
            "embedding": _fake_embedding(1),
            "metadata": {"source": "/tmp/a.txt", "chunk_index": 0, "total_chunks": 1},
        },
        {
            "id": "doc2",
            "text": "Chroma stores vectors locally",
            "embedding": _fake_embedding(2),
            "metadata": {"source": "/tmp/b.txt", "chunk_index": 0, "total_chunks": 1},
        },
    ]
    upsert_documents(docs)
    assert count_documents() == 2

    results = search(_fake_embedding(1), top_k=5)
    assert len(results) >= 1
    assert "text" in results[0]


def test_search_empty_collection():
    purge_collection()
    assert count_documents() == 0
    results = search(_fake_embedding(3), top_k=5)
    assert results == []


def test_search_top_k_larger_than_count():
    purge_collection()
    upsert_documents(
        [
            {
                "id": "only",
                "text": "one doc",
                "embedding": _fake_embedding(4),
                "metadata": {"source": "/tmp/x.txt", "chunk_index": 0, "total_chunks": 1},
            }
        ]
    )
    results = search(_fake_embedding(4), top_k=100)
    assert len(results) == 1
