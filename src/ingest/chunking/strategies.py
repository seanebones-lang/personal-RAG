"""Pluggable chunking strategies with metadata-aware splits."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from src.config import get_settings


@dataclass
class TextChunk:
    text: str
    extra: dict


_FENCE_RE = re.compile(r"^```[\w]*$", re.MULTILINE)


def chunk_document(text: str, file_path: Path) -> List[TextChunk]:
    """Split document text using configured strategy and file-type rules."""
    settings = get_settings()
    suffix = file_path.suffix.lower()

    if suffix == ".py":
        return _chunk_python(text, settings)
    if suffix in {".md", ".markdown"}:
        return _chunk_markdown(text, settings)

    strategy = settings.chunk_strategy
    if strategy == "recursive":
        parts = _recursive_split(text, settings.chunk_min_size, settings.chunk_max_size)
    elif strategy == "semantic":
        parts = _semantic_split(text, settings)
    else:
        parts = _char_split(text, settings.chunk_size, settings.chunk_overlap)

    return [TextChunk(text=p, extra={}) for p in parts if p.strip()]


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


def _semantic_split(text: str, settings) -> List[str]:
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


def _chunk_markdown(text: str, settings) -> List[TextChunk]:
    sections = _split_markdown_sections(text)
    chunks: List[TextChunk] = []
    for title, body in sections:
        if settings.chunk_strategy == "char":
            parts = _char_split(body, settings.chunk_size, settings.chunk_overlap)
        elif settings.chunk_strategy == "recursive":
            parts = _recursive_split(body, settings.chunk_min_size, settings.chunk_max_size)
        else:
            parts = _semantic_split(body, settings)
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


def _chunk_python(text: str, settings) -> List[TextChunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        parts = _recursive_split(text, settings.chunk_min_size, settings.chunk_max_size)
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
        parts = _recursive_split(text, settings.chunk_min_size, settings.chunk_max_size)
        return [TextChunk(text=p, extra={}) for p in parts]
    return chunks
