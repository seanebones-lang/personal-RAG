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
