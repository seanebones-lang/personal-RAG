"""Optional OCR parser for images (and basic scanned PDFs).

Install with:
    pip install "personalragvault[ocr]"
System requirement: Tesseract OCR binary must be installed
(https://tesseract-ocr.github.io/tessdoc/)

Enhancements: image preprocessing (grayscale, contrast, denoising) for robustness.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.ingest.parsers.base import BaseParser, ExtractedDocument

logger = logging.getLogger(__name__)


class OCRParser(BaseParser):
    """Extracts text from images using Tesseract OCR with preprocessing."""

    extensions = frozenset({".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"})

    def __init__(self):
        self._ocr_available = False
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter  # noqa: F401

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
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        except ImportError:
            return []

        try:
            img: Image.Image = Image.open(file_path)
            # Robustness enhancements: convert to grayscale, enhance contrast, sharpen
            if img.mode != "L":
                img = img.convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            # Optional deskew / invert if very dark (simple heuristic)
            inverted = ImageOps.invert(img)
            # getextrema() is per band: a flat (min, max) pair for "L",
            # one pair per band otherwise — take the overall minimum.
            band_mins = [e[0] if isinstance(e, tuple) else e for e in inverted.getextrema()]
            if min(band_mins) < 50:  # rough dark check
                img = inverted

            text = pytesseract.image_to_string(img)
            if text.strip():
                return [
                    ExtractedDocument(
                        text=text.strip(),
                        extra_metadata={
                            "ocr": True,
                            "format": file_path.suffix.lower(),
                            "preprocessed": True,
                        },
                    )
                ]
        except Exception as exc:
            logger.warning("OCR extraction failed for %s: %s", file_path, exc)

        return []
