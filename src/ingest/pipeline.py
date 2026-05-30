"""Build chunk documents from files for embedding."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.config import get_settings
from src.ingest.chunking import chunk_text
from src.ingest.ingest import discover_files, extract_text, validate_ingest_path

logger = logging.getLogger(__name__)


def make_chunk_id(source: str, chunk_index: int, text: str) -> str:
    payload = f"{source}:{chunk_index}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def build_documents_from_folder(
    folder: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
) -> List[Dict[str, Any]]:
    """Discover files, extract text, chunk, and return doc dicts (no embeddings)."""
    validated = validate_ingest_path(folder, allow_outside_home=allow_outside_home)
    settings = get_settings()
    files = discover_files(validated, recursive=recursive)
    docs: List[Dict[str, Any]] = []

    for file_path in files:
        text = extract_text(file_path)
        if not text.strip():
            continue
        source = str(file_path.resolve())
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            docs.append(
                {
                    "id": make_chunk_id(source, idx, chunk),
                    "text": chunk,
                    "metadata": {
                        "source": source,
                        "chunk_index": idx,
                        "total_chunks": total,
                    },
                }
            )
    return docs
