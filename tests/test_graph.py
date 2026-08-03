"""Wikilink graph helpers (mocked corpus)."""

from src.retrieval import graph


def test_neighbors_out_and_in(monkeypatch):
    corpus = [
        {
            "id": "1",
            "text": "a",
            "metadata": {
                "source": "/vault/Alpha.md",
                "wikilinks": "Beta,Gamma",
            },
        },
        {
            "id": "2",
            "text": "b",
            "metadata": {
                "source": "/vault/Beta.md",
                "wikilinks": "Alpha",
            },
        },
        {
            "id": "3",
            "text": "c",
            "metadata": {"source": "/vault/Gamma.md", "wikilinks": ""},
        },
    ]
    monkeypatch.setattr(graph, "fetch_corpus", lambda limit=None: corpus)

    out = graph.neighbors("Alpha", direction="out")
    assert out["outbound"] == ["Beta", "Gamma"]
    assert "Beta" in out["neighbors"]

    inn = graph.neighbors("Alpha", direction="in")
    assert inn["inbound"] == ["Beta"]

    both = graph.neighbors("Beta.md", direction="both")
    assert "Alpha" in both["neighbors"]
    assert both["notes_indexed"] == 3


def test_export_edges(monkeypatch):
    corpus = [
        {
            "id": "1",
            "text": "a",
            "metadata": {"source": "/v/A.md", "wikilinks": "B"},
        },
        {
            "id": "2",
            "text": "b",
            "metadata": {"source": "/v/B.md", "wikilinks": "A"},
        },
    ]
    monkeypatch.setattr(graph, "fetch_corpus", lambda limit=None: corpus)
    edges = graph.export_edges()
    assert {"from": "A", "to": "B"} in edges
    assert {"from": "B", "to": "A"} in edges
