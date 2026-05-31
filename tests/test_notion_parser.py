"""Tests for Notion parser."""

from pathlib import Path

import pytest

from src.ingest.parsers.notion import NotionParser


@pytest.fixture
def notion_path():
    return Path(__file__).parent / "fixtures" / "sample_notion.md"


def test_notion_parser(notion_path):
    parser = NotionParser()
    docs = parser.extract(notion_path)

    assert len(docs) == 1
    doc = docs[0]

    assert "Research Notes" in doc.text or "personal RAG" in doc.text
    assert doc.extra_metadata["format"] == "notion"
    assert "rag" in doc.extra_metadata.get("tags", "").lower()
    assert "2024-05-01" in doc.extra_metadata.get("created", "")
