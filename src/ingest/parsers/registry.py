"""Parser registry — dispatch by file extension."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Type

from src.ingest.parsers.base import BaseParser, ExtractedDocument
from src.ingest.parsers.bookmarks import BookmarksHTMLParser
from src.ingest.parsers.eml import EmlParser
from src.ingest.parsers.ics import IcsParser
from src.ingest.parsers.mbox import MboxParser
from src.ingest.parsers.obsidian import ObsidianMarkdownParser
from src.ingest.parsers.pinboard import PinboardParser
from src.ingest.parsers.raindrop import RaindropParser
from src.ingest.parsers.telegram import TelegramParser

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, BaseParser] = {}


def _register(parser_cls: Type[BaseParser]) -> None:
    instance = parser_cls()
    for ext in instance.extensions:
        _REGISTRY[ext] = instance


def _init_registry() -> None:
    if _REGISTRY:
        return
    _register(EmlParser)
    _register(MboxParser)
    _register(TelegramParser)
    _register(ObsidianMarkdownParser)
    _register(IcsParser)  # Calendar data (.ics)
    _register(BookmarksHTMLParser)  # Chrome/Edge/Brave bookmark HTML exports
    _register(RaindropParser)       # Raindrop.io JSON exports
    _register(PinboardParser)       # Pinboard JSON exports

    # Optional OCR support (only if user installed with [ocr] extra and tesseract is present)
    try:
        from src.ingest.parsers.ocr import OCRParser
        ocr_instance = OCRParser()
        if getattr(ocr_instance, "_ocr_available", False):
            _register(OCRParser)
            logger.info("OCR parser registered for image files")
    except Exception:
        pass  # OCR not available — this is fine


def extract_documents(file_path: Path, fallback_text: str) -> List[ExtractedDocument]:
    """Use registered parser or wrap fallback plain text."""
    _init_registry()
    ext = file_path.suffix.lower()
    parser = _REGISTRY.get(ext)
    if parser:
        try:
            docs = parser.extract(file_path)
            if docs:
                return docs
        except Exception as exc:
            logger.warning("Parser failed for %s: %s", file_path, exc)
    if ext == ".json" and file_path.name == "result.json":
        return []
    if fallback_text.strip():
        return [ExtractedDocument(text=fallback_text, extra_metadata={"format": ext or "plain"})]
    return []


def registered_extensions() -> frozenset[str]:
    _init_registry()
    return frozenset(_REGISTRY.keys())
