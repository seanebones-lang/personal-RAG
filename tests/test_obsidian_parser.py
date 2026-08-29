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


def test_obsidian_hq_frontmatter_and_yaml_lists(tmp_path):
    md = tmp_path / "client.md"
    md.write_text(
        "---\n"
        "type: project\n"
        "status: waiting\n"
        "priority: primary\n"
        "area: client\n"
        "source: /Users/example/project\n"
        "updated: 2026-08-29\n"
        "tags:\n"
        "  - project\n"
        "  - client\n"
        "aliases: [JP, JP Transmission]\n"
        "ignored_nested:\n"
        "  key: value\n"
        "---\n\n"
        "Current client truth.\n",
        encoding="utf-8",
    )
    doc = ObsidianMarkdownParser().extract(md)[0]
    meta = doc.extra_metadata
    assert meta["fm_type"] == "project"
    assert meta["fm_status"] == "waiting"
    assert meta["fm_priority"] == "primary"
    assert meta["fm_area"] == "client"
    assert meta["fm_source"] == "/Users/example/project"
    assert meta["fm_updated"] == "2026-08-29"
    assert meta["fm_tags"] == "project,client"
    assert meta["fm_aliases"] == "JP,JP Transmission"
    assert "fm_ignored_nested" not in meta


def test_obsidian_malformed_frontmatter_is_not_guessed(tmp_path):
    md = tmp_path / "broken.md"
    md.write_text("---\ntype: project\nstatus: current\nNo closing fence\n", encoding="utf-8")
    doc = ObsidianMarkdownParser().extract(md)[0]
    assert "fm_type" not in doc.extra_metadata
    assert doc.text.startswith("---")
