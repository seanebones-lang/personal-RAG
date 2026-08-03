from pathlib import Path

from src.ingest.parsers.eml import EmlParser
from src.ingest.parsers.registry import extract_documents, reset_registry_for_tests


def test_eml_parser_fixture():
    fixture = Path(__file__).parent / "fixtures" / "sample.eml"
    docs = EmlParser().extract(fixture)
    assert len(docs) == 1
    assert "invoice" in docs[0].text.lower()
    assert docs[0].extra_metadata.get("format") == "eml"


def test_registry_eml(tmp_path):
    eml = tmp_path / "mail.eml"
    eml.write_text(
        "From: a@b.com\nSubject: Hi\n\nBody text here.\n",
        encoding="utf-8",
    )
    docs = extract_documents(eml, "")
    assert len(docs) == 1
    assert "Body text" in docs[0].text


def test_registry_md_uses_obsidian_wikilinks(tmp_path):
    """Notion must not shadow Obsidian for ordinary .md files."""
    reset_registry_for_tests()
    md = tmp_path / "note.md"
    md.write_text("# Note\n\nSee [[Other]] and [[Hub]].\n", encoding="utf-8")
    docs = extract_documents(md, "fallback")
    assert len(docs) == 1
    assert docs[0].extra_metadata.get("format") == "obsidian"
    assert docs[0].extra_metadata.get("wikilink_count") == 2
    assert "Other" in docs[0].extra_metadata.get("wikilinks", "")
