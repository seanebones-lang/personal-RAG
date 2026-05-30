from pathlib import Path
from typing import List
import os

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".json"}

def discover_files(folder: Path) -> List[Path]:
    """Find supported files in a folder (non-recursive for safety)"""
    files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(f)
    return files

def extract_text(file_path: Path) -> str:
    """Basic text extraction"""
    if file_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    else:
        return file_path.read_text(encoding="utf-8", errors="ignore")