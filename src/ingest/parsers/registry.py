"""Parser registry — dispatch by file extension (ordered multi-parser)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Type

from src.ingest.parsers.base import BaseParser, ExtractedDocument
from src.ingest.parsers.bookmarks import BookmarksHTMLParser
from src.ingest.parsers.eml import EmlParser
from src.ingest.parsers.epub import EpubParser
from src.ingest.parsers.ics import IcsParser
from src.ingest.parsers.mbox import MboxParser
from src.ingest.parsers.notion import NotionParser
from src.ingest.parsers.obsidian import ObsidianMarkdownParser
from src.ingest.parsers.pinboard import PinboardParser
from src.ingest.parsers.raindrop import RaindropParser
from src.ingest.parsers.telegram import TelegramParser
from src.ingest.parsers.whatsapp import WhatsAppParser

logger = logging.getLogger(__name__)

# Multiple parsers may share an extension; tried in registration order until one
# returns documents (e.g. Notion returns [] for non-Notion .md, then Obsidian).
_REGISTRY: Dict[str, List[BaseParser]] = {}


def _register(parser_cls: Type[BaseParser]) -> None:
    instance = parser_cls()
    for ext in instance.extensions:
        _REGISTRY.setdefault(ext, []).append(instance)


def _init_registry() -> None:
    if _REGISTRY:
        return
    _register(EmlParser)
    _register(MboxParser)
    _register(TelegramParser)
    _register(IcsParser)
    _register(BookmarksHTMLParser)
    _register(RaindropParser)
    _register(PinboardParser)
    _register(WhatsAppParser)
    # .md: Notion only when heuristics match (else []); Obsidian enriches the rest
    _register(NotionParser)
    _register(ObsidianMarkdownParser)
    _register(EpubParser)

    try:
        from src.ingest.parsers.ocr import OCRParser

        ocr_instance = OCRParser()
        if getattr(ocr_instance, "_ocr_available", False):
            _register(OCRParser)
            logger.info("OCR parser registered for image files")
    except Exception:
        pass


def extract_documents(file_path: Path, fallback_text: str) -> List[ExtractedDocument]:
    """Use registered parsers (in order) or wrap fallback plain text."""
    _init_registry()
    ext = file_path.suffix.lower()
    for parser in _REGISTRY.get(ext, []):
        try:
            docs = parser.extract(file_path)
            if docs:
                return docs
        except Exception as exc:
            logger.warning("Parser failed for %s (%s): %s", file_path, type(parser).__name__, exc)
    if ext == ".json" and file_path.name == "result.json":
        return []
    if fallback_text.strip():
        return [ExtractedDocument(text=fallback_text, extra_metadata={"format": ext or "plain"})]
    return []


def registered_extensions() -> frozenset[str]:
    _init_registry()
    return frozenset(_REGISTRY.keys())


def reset_registry_for_tests() -> None:
    """Clear registry so tests can re-init after monkeypatches."""
    _REGISTRY.clear()
