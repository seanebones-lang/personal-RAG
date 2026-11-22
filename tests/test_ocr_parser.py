"""OCR parser tests (preprocessing path; tesseract boundary mocked)."""

from pathlib import Path

import pytest

from src.ingest.parsers.ocr import OCRParser

pytesseract = pytest.importorskip("pytesseract")
PIL = pytest.importorskip("PIL")


def _make_parser(monkeypatch) -> OCRParser:
    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.0.0")
    monkeypatch.setattr(
        pytesseract, "image_to_string", lambda img: "Fictional scanned memo text"
    )
    return OCRParser()


def _write_png(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (8, 8), (210, 210, 210)).save(path)


def test_ocr_extract_bright_image(monkeypatch, tmp_path):
    png = tmp_path / "bright.png"
    _write_png(png)
    docs = _make_parser(monkeypatch).extract(png)
    assert len(docs) == 1
    assert "Fictional scanned memo text" in docs[0].text


def test_ocr_extract_with_per_band_extrema(monkeypatch, tmp_path):
    """Regression: the dark-check compares getextrema()[0] against an int,
    but getextrema() is per band — one (min, max) pair per band for a
    multi-band image, so [0] can be a tuple and the comparison raises
    TypeError (silently swallowed by extract's catch-all). Feed the
    tuple-shaped extrema through the real extract path."""
    from PIL import ImageOps

    class _Inverted:
        def getextrema(self):
            return ((10, 200), (20, 210), (30, 220))

    monkeypatch.setattr(ImageOps, "invert", lambda img: _Inverted())
    png = tmp_path / "scan.png"
    _write_png(png)
    docs = _make_parser(monkeypatch).extract(png)
    assert len(docs) == 1
    assert "Fictional scanned memo text" in docs[0].text
