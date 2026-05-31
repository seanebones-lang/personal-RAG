"""Tests for Raindrop.io and Pinboard bookmark parsers."""

from pathlib import Path

import pytest

from src.ingest.parsers.pinboard import PinboardParser
from src.ingest.parsers.raindrop import RaindropParser


@pytest.fixture
def raindrop_path():
    return Path(__file__).parent / "fixtures" / "sample_raindrop.json"


@pytest.fixture
def pinboard_path():
    return Path(__file__).parent / "fixtures" / "sample_pinboard.json"


def test_raindrop_parser(raindrop_path):
    parser = RaindropParser()
    docs = parser.extract(raindrop_path)

    assert len(docs) == 2

    first = docs[0]
    assert "PersonalRAGVault" in first.text
    assert first.extra_metadata["url"] == "https://github.com/seanebones-lang/personal-RAG"
    assert first.extra_metadata["folder"] == "AI Tools"
    assert first.extra_metadata["format"] == "raindrop"
    assert "rag" in first.extra_metadata.get("tags", "")


def test_pinboard_parser(pinboard_path):
    parser = PinboardParser()
    docs = parser.extract(pinboard_path)

    assert len(docs) == 2

    first = docs[0]
    assert "PersonalRAGVault" in first.text
    assert first.extra_metadata["url"] == "https://github.com/seanebones-lang/personal-RAG"
    assert first.extra_metadata["format"] == "pinboard"
    assert "local-first" in first.extra_metadata.get("tags", "")
    assert "Great local RAG tool" in first.text  # extended notes
