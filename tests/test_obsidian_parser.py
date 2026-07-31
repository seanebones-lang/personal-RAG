from src.ingest.parsers.obsidian import ObsidianMarkdownParser, extract_wikilinks


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


def test_obsidian_wikilinks(tmp_path):
    body = "See [[Project Alpha|Alpha]] and [[Index#Heading]] plus ![[Embed Note]]."
    links = extract_wikilinks(body)
    assert "Project Alpha" in links
    assert "Index" in links
    assert "Embed Note" in links

    md = tmp_path / "graph.md"
    md.write_text("Link to [[Daily/2026-07-30]] and [[Hub]].\n", encoding="utf-8")
    docs = ObsidianMarkdownParser().extract(md)
    assert docs[0].extra_metadata.get("wikilink_count") == 2
    assert "Hub" in docs[0].extra_metadata.get("wikilinks", "")
