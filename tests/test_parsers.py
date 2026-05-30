from pathlib import Path

from src.ingest.parsers.eml import EmlParser
from src.ingest.parsers.registry import extract_documents


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
