from pathlib import Path

from src.ingest.chunking.strategies import chunk_document


def test_markdown_preserves_code_fence():
    text = "# Title\n\n```python\nprint('stay')\n```\n\nParagraph after."
    chunks = chunk_document(text, Path("note.md"))
    assert len(chunks) >= 1
    combined = "\n".join(c.text for c in chunks)
    assert "print('stay')" in combined


def test_recursive_strategy(monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_STRATEGY", "recursive")
    monkeypatch.setenv("PRV_CHUNK_MAX_SIZE", "100")
    monkeypatch.setenv("PRV_CHUNK_MIN_SIZE", "50")
    from src.config import reset_settings

    reset_settings()
    text = "Para one.\n\n" + ("Para two words. " * 20)
    chunks = chunk_document(text, Path("doc.txt"))
    assert len(chunks) > 1


def test_strategy_by_ext(monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_STRATEGY", "char")
    monkeypatch.setenv("PRV_CHUNK_STRATEGY_BY_EXT", ".md:recursive")
    monkeypatch.setenv("PRV_CHUNK_MAX_SIZE", "200")
    monkeypatch.setenv("PRV_CHUNK_MIN_SIZE", "50")
    from src.config import reset_settings

    reset_settings()
    long_body = "Word. " * 200
    md_chunks = chunk_document(long_body, Path("note.md"))
    txt_chunks = chunk_document(long_body, Path("note.txt"))
    assert len(md_chunks) >= 1
    assert len(txt_chunks) >= 1


def test_semantic_embed_mocked(monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_STRATEGY", "semantic_embed")
    monkeypatch.setenv("PRV_CHUNK_MAX_SIZE", "500")
    monkeypatch.setenv("PRV_SEMANTIC_THRESHOLD", "0.5")
    from src.config import reset_settings

    reset_settings()

    def fake_embed(texts, show_progress=True):
        import numpy as np

        out = []
        for i, _ in enumerate(texts):
            v = np.zeros(8)
            v[0] = 1.0 if i % 2 == 0 else 0.2
            out.append(v)
        return out

    monkeypatch.setattr("src.embed.embedder.embed_texts", fake_embed)
    text = "First sentence here. Second sentence follows. Third one ends."
    chunks = chunk_document(text, Path("article.txt"))
    assert len(chunks) >= 1
