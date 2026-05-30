"""File discovery and text extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.config import get_settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".json",
    ".docx",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".htm",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".rst",
}


def validate_ingest_path(folder: Path, allow_outside_home: bool = False) -> Path:
    """Resolve and validate ingest directory."""
    resolved = folder.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {resolved}")
    if not allow_outside_home:
        home = Path.home().resolve()
        try:
            resolved.relative_to(home)
        except ValueError:
            raise ValueError(
                f"Path {resolved} is outside home directory. Use --allow-outside-home to override."
            )
    return resolved


def discover_files(folder: Path, recursive: bool = False) -> List[Path]:
    """Find supported files in a folder."""
    files: List[Path] = []
    if recursive:
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(f)
    else:
        for f in folder.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(f)
    return sorted(files)


def _check_file_size(file_path: Path) -> bool:
    max_bytes = get_settings().max_file_bytes
    size = file_path.stat().st_size
    if size > max_bytes:
        logger.warning(
            "Skipping %s (%d bytes > max %d)",
            file_path,
            size,
            max_bytes,
        )
        return False
    return True


def extract_text(file_path: Path) -> str:
    """Extract text from supported file types."""
    if not _check_file_size(file_path):
        return ""

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix == ".docx":
        return _extract_docx(file_path)
    return _extract_plain(file_path)


def _extract_pdf(file_path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("Failed to extract PDF %s: %s", file_path, exc)
        return ""


def _extract_docx(file_path: Path) -> str:
    try:
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        logger.warning("Failed to extract DOCX %s: %s", file_path, exc)
        return ""


def _extract_plain(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", file_path, exc)
        return ""
