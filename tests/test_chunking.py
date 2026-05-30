from src.ingest.chunking import chunk_text


def test_empty_text():
    assert chunk_text("", 100, 10) == []
    assert chunk_text("   ", 100, 10) == []


def test_short_text_single_chunk():
    assert chunk_text("hello world", 100, 10) == ["hello world"]


def test_overlapping_chunks():
    text = "a" * 250
    chunks = chunk_text(text, 100, 20)
    assert len(chunks) >= 2
    assert all(len(c) <= 100 for c in chunks)
