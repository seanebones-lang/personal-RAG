
from src.ingest.parsers.obsidian import ObsidianMarkdownParser


def test_obsidian_frontmatter_and_tags(tmp_path):
    md = tmp_path / "note.md"
    md.write_text(
        "---\ntitle: My Note\ntags: work\n---\n\n# Heading\n\nContent with #tag1 here.\n",
        encoding="utf-8",
    )
    docs = ObsidianMarkdownParser().extract(md)
    assert len(docs) == 1
    assert "Content with" in docs[0].text
    assert docs[0].extra_metadata.get("fm_title") == "My Note"
    assert "tag1" in docs[0].extra_metadata.get("obsidian_tags", "")
