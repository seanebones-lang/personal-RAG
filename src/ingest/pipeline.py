"""Build chunk documents from files for embedding."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

from src.ingest.chunking import TextChunk, chunk_document
from src.ingest.ingest import discover_files, extract_text, validate_ingest_path
from src.ingest.metadata import build_chunk_metadata
from src.ingest.parsers.registry import extract_documents
from src.store.file_cache import record_file, should_skip_file

logger = logging.getLogger(__name__)


def make_chunk_id(source: str, chunk_index: int, text: str) -> str:
    payload = f"{source}:{chunk_index}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def _docs_for_file(
    file_path: Path,
    ingest_root: Path,
) -> List[Dict[str, Any]]:
    """Extract + chunk a single file into document dicts (no embeddings)."""
    fallback = extract_text(file_path)
    extracted_list = extract_documents(file_path, fallback)
    if not extracted_list:
        return []

    docs: List[Dict[str, Any]] = []
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
    return docs


def iter_file_documents(
    folder: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force_reingest: bool = False,
) -> Iterator[Tuple[Path, List[Dict[str, Any]], Dict[str, Any]]]:
    """Yield (path, docs, meta) per discovered file. Skipped files yield empty docs."""
    validated = validate_ingest_path(folder, allow_outside_home=allow_outside_home)
    ingest_root = validated.resolve()
    files = discover_files(validated, recursive=recursive)
    total = len(files)

    for file_path in files:
        if should_skip_file(file_path, force=force_reingest):
            logger.info("Skipping unchanged file: %s", file_path)
            yield file_path, [], {"files_total": total, "skipped": True}
            continue

        docs = _docs_for_file(file_path, ingest_root)
        if docs:
            record_file(file_path)
        yield file_path, docs, {"files_total": total, "skipped": False}


def build_documents_from_folder(
    folder: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force_reingest: bool = False,
) -> List[Dict[str, Any]]:
    """Discover files, extract text, chunk, and return doc dicts (no embeddings)."""
    docs: List[Dict[str, Any]] = []
    for _path, file_docs, meta in iter_file_documents(
        folder,
        recursive=recursive,
        allow_outside_home=allow_outside_home,
        force_reingest=force_reingest,
    ):
        if meta.get("skipped"):
            continue
        docs.extend(file_docs)
    return docs
