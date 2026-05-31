"""Tests for browser bookmark parsers."""

from pathlib import Path

import pytest

from src.ingest.parsers.bookmarks import BookmarksHTMLParser


@pytest.fixture
def sample_bookmarks_path():
    return Path(__file__).parent / "fixtures" / "sample_bookmarks.html"


def test_chrome_bookmarks_html_parsing(sample_bookmarks_path):
    parser = BookmarksHTMLParser()
    docs = parser.extract(sample_bookmarks_path)

    assert len(docs) == 3

    # Check first bookmark
    first = docs[0]
    assert "PersonalRAGVault" in first.text
    assert first.extra_metadata["url"] == "https://github.com/seanebones-lang/personal-RAG"
    assert first.extra_metadata["folder"] == "Work"
    assert first.extra_metadata["format"] == "browser_bookmark"

    # Check that folder hierarchy is captured
    second = docs[1]
    assert "Retrieval Augmented Generation" in second.text
    assert second.extra_metadata["folder"] == "Work"

    # Check tags were captured
    assert "rag" in second.extra_metadata.get("tags", "").lower()

    # Check third bookmark under different folder
    third = docs[2]
    assert third.extra_metadata["folder"] == "Reading"
    assert "Wikipedia" in third.text