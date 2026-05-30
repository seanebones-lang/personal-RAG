"""Build chunk documents from files for embedding."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.ingest.chunking import TextChunk, chunk_document
from src.ingest.ingest import discover_files, extract_text, validate_ingest_path
from src.ingest.metadata import build_chunk_metadata
from src.ingest.parsers.registry import extract_documents
from src.store.file_cache import record_file, should_skip_file

logger = logging.getLogger(__name__)


def make_chunk_id(source: str, chunk_index: int, text: str) -> str:
    payload = f"{source}:{chunk_index}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def build_documents_from_folder(
    folder: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force_reingest: bool = False,
) -> List[Dict[str, Any]]:
    """Discover files, extract text, chunk, and return doc dicts (no embeddings)."""
    validated = validate_ingest_path(folder, allow_outside_home=allow_outside_home)
    ingest_root = validated.resolve()
    files = discover_files(validated, recursive=recursive)
    docs: List[Dict[str, Any]] = []

    for file_path in files:
        if should_skip_file(file_path, force=force_reingest):
            logger.info("Skipping unchanged file: %s", file_path)
            continue

        fallback = extract_text(file_path)
        extracted_list = extract_documents(file_path, fallback)
        if not extracted_list:
            continue

        file_had_chunks = False
        for doc_idx, extracted in enumerate(extracted_list):
            text = extracted.text
            if not text.strip():
                continue
            source = str(file_path.resolve())
            if len(extracted_list) > 1:
                source = f"{source}#doc{doc_idx}"

            text_chunks: List[TextChunk] = chunk_document(text, file_path)
            total = len(text_chunks)

            for idx, tchunk in enumerate(text_chunks):
                extra = dict(extracted.extra_metadata)
                extra["doc_index"] = doc_idx
                extra.update(tchunk.extra)
                docs.append(
                    {
                        "id": make_chunk_id(source, idx, tchunk.text),
                        "text": tchunk.text,
                        "metadata": build_chunk_metadata(
                            file_path,
                            ingest_root,
                            idx,
                            total,
                            extra=extra,
                        ),
                    }
                )
                file_had_chunks = True

        if file_had_chunks:
            record_file(file_path)

    return docs
