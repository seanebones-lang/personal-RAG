"""Unit tests for recursive ingest noise-dir excludes."""

from pathlib import Path

from src.config import reset_settings
from src.ingest.ingest import discover_files


def test_discover_skips_default_obsidian_noise(tmp_path: Path) -> None:
    """Nested .obsidian/* is ignored; real notes are discovered."""
    reset_settings()
    note = tmp_path / "note.md"
    note.write_text("# real note\n", encoding="utf-8")
    obsidian = tmp_path / ".obsidian"
    obsidian.mkdir()
    (obsidian / "app.json").write_text('{"theme": "dark"}', encoding="utf-8")
    nested = tmp_path / "Daily"
    nested.mkdir()
    (nested / "day.md").write_text("daily\n", encoding="utf-8")
    deep_obs = nested / ".obsidian"
    deep_obs.mkdir()
    (deep_obs / "workspace.json").write_text("{}", encoding="utf-8")

    files = discover_files(tmp_path, recursive=True)
    names = {f.name for f in files}
    assert names == {"note.md", "day.md"}
    assert all(".obsidian" not in f.parts for f in files)


def test_discover_skips_git_venv_node_modules(tmp_path: Path) -> None:
    reset_settings()
    (tmp_path / "keep.md").write_text("keep", encoding="utf-8")
    for dirname, fname in (
        (".git", "HEAD.md"),
        (".venv", "lib.py"),
        ("venv", "site.py"),
        ("node_modules", "pkg.js"),
        ("__pycache__", "mod.py"),
    ):
        d = tmp_path / dirname
        d.mkdir()
        (d / fname).write_text("noise", encoding="utf-8")

    files = discover_files(tmp_path, recursive=True)
    assert [f.name for f in files] == ["keep.md"]


def test_discover_extra_exclude_dirs_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRV_INGEST_EXCLUDE_DIRS", "drafts,private_notes")
    reset_settings()
    (tmp_path / "ok.md").write_text("ok", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "wip.md").write_text("wip", encoding="utf-8")
    private = tmp_path / "private_notes"
    private.mkdir()
    (private / "secret.md").write_text("secret", encoding="utf-8")

    files = discover_files(tmp_path, recursive=True)
    assert [f.name for f in files] == ["ok.md"]


def test_discover_exclude_dirs_case_sensitive(tmp_path: Path, monkeypatch) -> None:
    """Extra excludes match path parts case-sensitively (env token not lowercased)."""
    monkeypatch.setenv("PRV_INGEST_EXCLUDE_DIRS", "Drafts")
    reset_settings()
    from src.config import get_settings

    excludes = get_settings().ingest_exclude_dirs
    assert "Drafts" in excludes
    assert "drafts" not in excludes

    upper = tmp_path / "Drafts"
    upper.mkdir()
    (upper / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "ok.md").write_text("ok", encoding="utf-8")

    files = discover_files(tmp_path, recursive=True)
    assert [f.name for f in files] == ["ok.md"]
