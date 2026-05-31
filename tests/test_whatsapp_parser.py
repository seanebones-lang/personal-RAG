"""Tests for WhatsApp chat parser."""

from pathlib import Path

import pytest

from src.ingest.parsers.whatsapp import WhatsAppParser


@pytest.fixture
def whatsapp_path():
    return Path(__file__).parent / "fixtures" / "sample_whatsapp.txt"


def test_whatsapp_parser(whatsapp_path):
    parser = WhatsAppParser()
    docs = parser.extract(whatsapp_path)

    assert len(docs) == 6

    first = docs[0]
    assert "RAG project" in first.text
    assert first.extra_metadata["sender"] == "John"
    assert first.extra_metadata["format"] == "whatsapp"
    assert first.extra_metadata["chat_name"]  # should be detected

    # Check media detection
    media_msg = docs[4]
    assert media_msg.extra_metadata["has_media"] is True

    # Check multi-line would work (though sample is single line)
    last = docs[-1]
    assert "Obsidian vault" in last.text
