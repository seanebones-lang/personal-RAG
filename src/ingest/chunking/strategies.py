"""Pluggable chunking strategies with metadata-aware splits."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

from src.config import get_settings, normalize_chunk_strategy
from src.ingest.chunking.context import get_chunk_strategy_override


@dataclass
class TextChunk:
    text: str
    extra: dict


_FENCE_RE = re.compile(r"^```[\w]*$", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def resolve_chunk_strategy(file_path: Path) -> str:
    """Effective strategy: override, per-extension map, then global default."""
    override = get_chunk_strategy_override()
    if override:
        return normalize_chunk_strategy(override)
    settings = get_settings()
    suffix = file_path.suffix.lower()
    if suffix in settings.chunk_strategy_by_ext:
        return settings.chunk_strategy_by_ext[suffix]
    return settings.chunk_strategy


def chunk_document(text: str, file_path: Path) -> List[TextChunk]:
    """Split document text using configured strategy and file-type rules."""
    settings = get_settings()
    strategy = resolve_chunk_strategy(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".py":
        return _chunk_python(text, settings, strategy)
    if suffix in {".md", ".markdown"}:
        return _chunk_markdown(text, settings, strategy)

    parts = _split_by_strategy(text, settings, strategy)
    return [TextChunk(text=p, extra={}) for p in parts if p.strip()]


def _split_by_strategy(text: str, settings, strategy: str) -> List[str]:
    if strategy == "recursive":
        return _recursive_split(text, settings.chunk_min_size, settings.chunk_max_size)
    if strategy in ("semantic", "prose"):
        return _prose_split(text, settings)
    if strategy == "semantic_embed":
        return _semantic_embed_split(text, settings)
    return _char_split(text, settings.chunk_size, settings.chunk_overlap)


def _char_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    from src.ingest.chunking.char import chunk_text

    return chunk_text(text, chunk_size, overlap)


def _recursive_split(text: str, min_size: int, max_size: int) -> List[str]:
    separators = ["\n\n", "\n", ". ", " "]
    return _split_recursive(text.strip(), separators, max_size, min_size)


def _split_recursive(text: str, separators: List[str], max_size: int, min_size: int) -> List[str]:
    if len(text) <= max_size:
        return [text] if text.strip() else []
    if not separators:
        return [text[i : i + max_size] for i in range(0, len(text), max_size)]

    sep = separators[0]
    rest = separators[1:]
    parts = text.split(sep) if sep != " " else text.split()
    chunks: List[str] = []
    current = ""
    joiner = "" if sep == " " else sep

    for i, part in enumerate(parts):
        piece = part if sep == " " else (joiner + part if i else part)
        candidate = (current + piece) if current else piece
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current.strip():
                if len(current) > max_size and rest:
                    chunks.extend(_split_recursive(current, rest, max_size, min_size))
                else:
                    chunks.append(current.strip())
            if len(part) > max_size and rest:
                chunks.extend(_split_recursive(part, rest, max_size, min_size))
            else:
                current = part.strip()
    if current.strip():
        if len(current) > max_size and rest:
            chunks.extend(_split_recursive(current, rest, max_size, min_size))
        else:
            chunks.append(current.strip())
    return chunks


def _prose_split(text: str, settings) -> List[str]:
    """Paragraph-first merge up to max chunk size, then recursive overflow."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    max_size = settings.chunk_max_size

    for para in paragraphs:
        if current_len + len(para) + 2 > max_size and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))

    out: List[str] = []
    for ch in chunks:
        if len(ch) > max_size:
            out.extend(_recursive_split(ch, settings.chunk_min_size, max_size))
        else:
            out.append(ch)
    return out


def _semantic_embed_split(text: str, settings) -> List[str]:
    """Split on embedding similarity breakpoints between sentences."""
    sentences = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
    if not sentences:
        return []
    if len(sentences) == 1:
        return sentences if len(sentences[0]) <= settings.chunk_max_size else _recursive_split(
            sentences[0], settings.chunk_min_size, settings.chunk_max_size
        )

    from src.embed.embedder import embed_texts

    vectors = embed_texts(sentences, show_progress=False)
    if len(vectors) < 2:
        return _merge_sentences_to_chunks(sentences, settings.chunk_max_size)

    groups: List[List[str]] = [[sentences[0]]]
    for i in range(1, len(sentences)):
        sim = _cosine_similarity(vectors[i - 1], vectors[i])
        if sim < settings.semantic_threshold:
            groups.append([sentences[i]])
        else:
            groups[-1].append(sentences[i])

    chunks: List[str] = []
    for group in groups:
        merged = " ".join(group)
        if len(merged) <= settings.chunk_max_size:
            chunks.append(merged)
        else:
            chunks.extend(
                _recursive_split(merged, settings.chunk_min_size, settings.chunk_max_size)
            )
    return chunks


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _merge_sentences_to_chunks(sentences: List[str], max_size: int) -> List[str]:
    chunks: List[str] = []
    current = ""
    for s in sentences:
        candidate = f"{current} {s}".strip() if current else s
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


def _chunk_markdown(text: str, settings, strategy: str) -> List[TextChunk]:
    sections = _split_markdown_sections(text)
    chunks: List[TextChunk] = []
    for title, body in sections:
        parts = _split_by_strategy(body, settings, strategy)
        for p in parts:
            extra = {"section_title": title[:200]} if title else {}
            chunks.append(TextChunk(text=p, extra=extra))
    return chunks


def _split_markdown_sections(text: str) -> List[Tuple[str, str]]:
    """Preserve fenced code blocks; split on headings."""
    lines = text.splitlines()
    sections: List[Tuple[str, str]] = []
    title = ""
    body_lines: List[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal body_lines, title
        body = "\n".join(body_lines).strip()
        if body:
            sections.append((title, body))
        body_lines = []

    for line in lines:
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            body_lines.append(line)
            continue
        if not in_fence and line.startswith("#"):
            flush()
            title = line.lstrip("#").strip()
            continue
        body_lines.append(line)
    flush()
    if not sections and text.strip():
        sections.append(("", text.strip()))
    return sections


def _chunk_python(text: str, settings, strategy: str) -> List[TextChunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        parts = _split_by_strategy(text, settings, strategy)
        return [TextChunk(text=p, extra={"chunk_kind": "python"}) for p in parts]

    lines = text.splitlines(keepends=True)
    chunks: List[TextChunk] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            segment = "".join(lines[node.lineno - 1 : node.end_lineno])
            if len(segment) <= settings.chunk_max_size:
                name = node.name
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                chunks.append(
                    TextChunk(
                        text=segment.strip(),
                        extra={"chunk_kind": kind, "symbol": name},
                    )
                )
            else:
                for p in _recursive_split(
                    segment, settings.chunk_min_size, settings.chunk_max_size
                ):
                    chunks.append(TextChunk(text=p, extra={"chunk_kind": "python"}))
    if not chunks:
        parts = _split_by_strategy(text, settings, strategy)
        return [TextChunk(text=p, extra={}) for p in parts]
    return chunks
