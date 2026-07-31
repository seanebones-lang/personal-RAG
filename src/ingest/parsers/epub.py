"""EPUB parser for e-books.

Optional dependency: ebooklib (pip install ebooklib)
Falls back to basic zipfile + html extraction if unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)


class EpubParser(BaseParser):
    """Extract text from EPUB files."""

    extensions = {".epub"}

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        try:
            from bs4 import BeautifulSoup
            from ebooklib import epub
            from ebooklib.utils import get_body_content

            book = epub.read_epub(str(file_path))
            texts = []
            for item in book.get_items():
                if item.get_type() == 9:  # ebooklib.ITEM_DOCUMENT
                    try:
                        soup = BeautifulSoup(get_body_content(item), "html.parser")
                        text = soup.get_text(separator=" ", strip=True)
                        if text.strip():
                            texts.append(text)
                    except Exception:
                        continue
            full_text = "\n\n".join(texts)
            if full_text.strip():
                return [ExtractedDocument(
                    text=full_text.strip(),
                    extra_metadata={"format": "epub", "title": book.title or file_path.name}
                )]
        except ImportError:
            logger.debug("ebooklib not installed; trying basic EPUB extraction")
        except Exception as exc:
            logger.warning("ebooklib EPUB extraction failed for %s: %s", file_path, exc)

        # Fallback: basic zip + html parse (no bs4 dependency in fallback for minimalism)
        try:
            import zipfile
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.texts = []
                def handle_data(self, data):
                    self.texts.append(data)

            texts = []
            with zipfile.ZipFile(file_path) as z:
                for name in z.namelist():
                    if name.endswith((".xhtml", ".html", ".htm")):
                        try:
                            content = z.read(name).decode("utf-8", errors="ignore")
                            parser = _TextExtractor()
                            parser.feed(content)
                            t = " ".join(parser.texts).strip()
                            if t:
                                texts.append(t)
                        except Exception:
                            continue
            full = "\n\n".join(texts)
            if full.strip():
                return [
                    ExtractedDocument(
                        text=full.strip(),
                        extra_metadata={"format": "epub", "fallback": True},
                    )
                ]
        except Exception as exc:
            logger.warning("Fallback EPUB extraction failed for %s: %s", file_path, exc)

        return []
