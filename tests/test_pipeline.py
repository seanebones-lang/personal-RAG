from src.ingest.pipeline import build_documents_from_folder, make_chunk_id


def test_build_documents_chunks(tmp_path, monkeypatch):
    monkeypatch.setenv("PRV_CHUNK_SIZE", "100")
    monkeypatch.setenv("PRV_CHUNK_OVERLAP", "20")
    from src.config import reset_settings

    reset_settings()

    long_text = "word " * 40
    (tmp_path / "doc.txt").write_text(long_text)
    docs = build_documents_from_folder(tmp_path, allow_outside_home=True)
    assert len(docs) > 1
    assert docs[0]["metadata"]["chunk_index"] == 0
    assert docs[0]["metadata"]["total_chunks"] == len(docs)


def test_stable_chunk_ids():
    a = make_chunk_id("/tmp/f.txt", 0, "hello")
    b = make_chunk_id("/tmp/f.txt", 0, "hello")
    c = make_chunk_id("/tmp/f.txt", 1, "hello")
    assert a == b
    assert a != c
