"""Optional OCR parser for images (and basic scanned PDFs).

Install with:
    pip install "personalragvault[ocr]"

System requirement: Tesseract OCR binary must be installed
(https://tesseract-ocr.github.io/tessdoc/)

If the extra or the binary is missing, ingestion gracefully skips OCR.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)


class OCRParser(BaseParser):
    """Extracts text from images using Tesseract OCR."""

    extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}

    def __init__(self):
        self._ocr_available = False
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            import pytesseract
            from PIL import Image  # noqa: F401

            try:
                pytesseract.get_tesseract_version()
                self._ocr_available = True
            except Exception:
                logger.debug("OCR: tesseract binary not found in PATH")
        except ImportError:
            pass

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        if not self._ocr_available:
            return []

        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return []

        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            if text.strip():
                return [ExtractedDocument(
                    text=text.strip(),
                    extra_metadata={"ocr": True, "format": file_path.suffix.lower()}
                )]
        except Exception as exc:
            logger.warning("OCR extraction failed for %s: %s", file_path, exc)

        return []
