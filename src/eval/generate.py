"""Synthetic evaluation dataset generation from vault or folder."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ingest.pipeline import build_documents_from_folder
from src.store.vectorstore import fetch_corpus


def _basename_hint(source: str) -> str:
    path = source.split("#")[0]
    return Path(path).name


def sample_chunks_from_vault(sample: int) -> List[Dict[str, Any]]:
    corpus = fetch_corpus(limit=50_000)
    if not corpus:
        return []
    k = min(sample, len(corpus))
    return random.sample(corpus, k)


def sample_chunks_from_folder(
    folder: Path,
    sample: int,
    recursive: bool = False,
    allow_outside_home: bool = False,
) -> List[Dict[str, Any]]:
    docs = build_documents_from_folder(
        folder,
        recursive=recursive,
        allow_outside_home=allow_outside_home,
        force_reingest=True,
    )
    if not docs:
        return []
    k = min(sample, len(docs))
    picked = random.sample(docs, k)
    return [
        {
            "id": d["id"],
            "text": d["text"],
            "metadata": d.get("metadata", {}),
        }
        for d in picked
    ]


def _ollama_question(chunk_text: str, source_hint: str) -> str:
    from src.ollama_client import generate_answer

    prompt = (
        "Write one short natural-language question that this text passage answers. "
        "Reply with only the question, no quotes or preamble.\n\n"
        f"Source file: {source_hint}\n\n"
        f"Passage:\n{chunk_text[:1500]}"
    )
    raw = generate_answer(prompt)
    line = raw.strip().splitlines()[0] if raw else ""
    line = re.sub(r"^Question:\s*", "", line, flags=re.I).strip()
    return line or f"What does {source_hint} say?"


def generate_dataset(
    path: Optional[Path] = None,
    sample: int = 10,
    use_ollama: bool = True,
    recursive: bool = False,
    allow_outside_home: bool = False,
    from_vault: bool = True,
) -> List[Dict[str, Any]]:
    """Build eval JSONL rows; set generated=true for human review."""
    if from_vault and path is None:
        chunks = sample_chunks_from_vault(sample)
    elif path is not None:
        if from_vault:
            chunks = sample_chunks_from_vault(sample)
            if not chunks:
                chunks = sample_chunks_from_folder(
                    path, sample, recursive=recursive, allow_outside_home=allow_outside_home
                )
        else:
            chunks = sample_chunks_from_folder(
                path, sample, recursive=recursive, allow_outside_home=allow_outside_home
            )
    else:
        chunks = sample_chunks_from_vault(sample)

    rows: List[Dict[str, Any]] = []
    for ch in chunks:
        meta = ch.get("metadata") or {}
        source = str(meta.get("source", meta.get("file_name", "unknown")))
        hint = _basename_hint(source)
        text = ch.get("text", "")
        if use_ollama:
            try:
                question = _ollama_question(text, hint)
            except Exception:
                question = f"What information is in {hint}?"
        else:
            snippet = text[:80].replace("\n", " ")
            question = f"What does this passage from {hint} discuss: {snippet}?"
        rows.append(
            {
                "question": question,
                "expected_source_contains": hint,
                "generated": True,
            }
        )
    return rows


def write_dataset(rows: List[Dict[str, Any]], output: Path) -> None:
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
