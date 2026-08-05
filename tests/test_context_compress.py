from src.ollama_client import _extract_key_sentences, build_tagged_context


def test_query_aware_sentence_pick():
    text = (
        "The weather was mild today. "
        "Bitcoin futures settled above the strike on Kalshi. "
        "I also bought milk at the store. "
        "Kalshi bitcoin market notes are in the journal."
    )
    out = _extract_key_sentences(text, max_sentences=2, query="kalshi bitcoin")
    lower = out.lower()
    assert "bitcoin" in lower or "kalshi" in lower
    # grocery sentence should not dominate
    assert "milk" not in lower or "kalshi" in lower


def test_build_tagged_context_passes_query():
    results = [
        {
            "text": "Alpha sentence about nothing. Beta sentence mentions invoice total clearly.",
            "metadata": {"source": "/a.md", "chunk_index": 0},
        }
    ]
    ctx = build_tagged_context(results, max_chars=500, compress=True, query="invoice total")
    assert "[Source:" in ctx
