
from src.ingest.metadata import build_chunk_metadata


def test_build_chunk_metadata(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    f = root / "notes.txt"
    f.write_text("hello")
    meta = build_chunk_metadata(f, root, 0, 1)
    assert meta["file_name"] == "notes.txt"
    assert meta["extension"] == ".txt"
    assert meta["chunk_index"] == 0
    assert "year" in meta
    assert meta["relative_path"] == "notes.txt"
