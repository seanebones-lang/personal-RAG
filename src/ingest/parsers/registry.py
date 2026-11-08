"""Parser registry — dispatch by file extension (ordered multi-parser)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Type

from src.config import get_settings
from src.ingest.parsers.base import BaseParser, ExtractedDocument
from src.ingest.parsers.bookmarks import BookmarksHTMLParser
from src.ingest.parsers.browser_history import BrowserHistoryParser
from src.ingest.parsers.csv_parser import CsvParser
from src.ingest.parsers.eml import EmlParser
from src.ingest.parsers.epub import EpubParser
from src.ingest.parsers.html_parser import HtmlMainContentParser
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
# Parsers may also claim exact file names regardless of suffix, for formats
# whose canonical name carries no extension (e.g. Chromium's "History").
_FILENAME_REGISTRY: Dict[str, List[BaseParser]] = {}


def _register(parser_cls: Type[BaseParser]) -> None:
    instance = parser_cls()
    for ext in instance.extensions:
        _REGISTRY.setdefault(ext, []).append(instance)
    for name in instance.filenames:
        _FILENAME_REGISTRY.setdefault(name, []).append(instance)


def _init_registry() -> None:
    if _REGISTRY:
        return
    _register(EmlParser)
    _register(MboxParser)
    _register(CsvParser)
    _register(TelegramParser)
    _register(IcsParser)
    # .html/.htm: bookmark exports are claimed by BookmarksHTMLParser
    # (it returns [] for anything else); the main-content parser takes
    # the generic pages it declines.
    _register(BookmarksHTMLParser)
    _register(HtmlMainContentParser)
    _register(RaindropParser)
    _register(PinboardParser)
    _register(WhatsAppParser)
    # .md: Notion only when heuristics match (else []); Obsidian enriches the rest
    _register(NotionParser)
    _register(ObsidianMarkdownParser)
    _register(EpubParser)

    # Browser history is opt-in (PRV_INGEST_BROWSER_HISTORY): browsing
    # history is sensitive, so the parser — and its .sqlite / "History"
    # claims on discovery — exists only when the user has enabled it.
    if get_settings().ingest_browser_history:
        _register(BrowserHistoryParser)
        logger.info("Browser history parser registered (opt-in enabled)")

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
    # An exact-name claim is the most specific claim a parser can make;
    # those parsers are tried before suffix claimants.
    claimants = _FILENAME_REGISTRY.get(file_path.name, [])
    ext = file_path.suffix.lower()
    claimants = claimants + _REGISTRY.get(ext, [])
    for parser in claimants:
        try:
            docs = parser.extract(file_path)
            if docs:
                return docs
        except Exception as exc:
            logger.warning("Parser failed for %s (%s): %s", file_path, type(parser).__name__, exc)
    if ext == ".json" and file_path.name == "result.json":
        return []
    if file_path.name == "History" or ext == ".sqlite":
        # Browser history stores are binary SQLite. When the opt-in
        # history parser declines one (or is disabled), never wrap the
        # database bytes as a plain-text document.
        return []
    if fallback_text.strip():
        return [ExtractedDocument(text=fallback_text, extra_metadata={"format": ext or "plain"})]
    return []


def registered_extensions() -> frozenset[str]:
    _init_registry()
    return frozenset(_REGISTRY.keys())


def registered_filenames() -> frozenset[str]:
    _init_registry()
    return frozenset(_FILENAME_REGISTRY.keys())


def reset_registry_for_tests() -> None:
    """Clear registry so tests can re-init after monkeypatches."""
    _REGISTRY.clear()
    _FILENAME_REGISTRY.clear()
