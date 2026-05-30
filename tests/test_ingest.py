from pathlib import Path

import pytest

from src.ingest.ingest import discover_files, extract_text, validate_ingest_path


def test_validate_missing_path(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        validate_ingest_path(missing)


def test_validate_not_directory(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        validate_ingest_path(f)


def test_validate_outside_home(tmp_path):
    outside = Path("/tmp") if Path("/tmp").exists() else tmp_path
    with pytest.raises(ValueError, match="outside home"):
        validate_ingest_path(outside, allow_outside_home=False)


def test_discover_non_recursive(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.pdf").write_bytes(b"%PDF")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("c")
    files = discover_files(tmp_path, recursive=False)
    names = {f.name for f in files}
    assert names == {"a.txt", "b.pdf"}


def test_discover_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("nested")
    files = discover_files(tmp_path, recursive=True)
    assert any(f.name == "c.md" for f in files)


def test_extract_txt(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello vault", encoding="utf-8")
    assert extract_text(p) == "hello vault"
