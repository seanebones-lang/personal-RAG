"""Parent expansion uses metadata filter, not full corpus scan."""

from __future__ import annotations

from unittest.mock import patch

from src.retrieval.parent import expand_parent_chunks


def test_expand_parent_uses_get_by_where():
    hit = {
        "id": "c1",
        "text": "middle chunk",
        "metadata": {"parent_id": "p1", "chunk_index": 1, "source": "/x.md"},
        "distance": 0.1,
    }
    siblings = [
        {
            "id": "c0",
            "text": "before",
            "metadata": {"parent_id": "p1", "chunk_index": 0},
        },
        hit,
        {
            "id": "c2",
            "text": "after",
            "metadata": {"parent_id": "p1", "chunk_index": 2},
        },
    ]
    with patch("src.store.vectorstore.get_by_where", return_value=siblings) as mock_get:
        out = expand_parent_chunks([hit])
    mock_get.assert_called()
    assert len(out) == 1
    assert out[0].get("parent_expanded") is True
    assert "before" in out[0]["text"]
    assert "after" in out[0]["text"]


def test_expand_parent_no_parent_id_passthrough():
    hit = {"id": "x", "text": "solo", "metadata": {}, "distance": 0.2}
    out = expand_parent_chunks([hit])
    assert out[0]["text"] == "solo"
    assert not out[0].get("parent_expanded")
