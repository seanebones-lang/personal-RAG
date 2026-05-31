"""Ollama generation helpers."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.config import get_settings

logger = logging.getLogger(__name__)


def check_ollama_model() -> None:
    """Raise RuntimeError if Ollama is unreachable or model is missing."""
    settings = get_settings()
    try:
        import ollama
    except ImportError as exc:
        raise RuntimeError("ollama package is not installed") from exc

    try:
        client = ollama.Client(host=settings.ollama_host)
        listed = client.list()
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {settings.ollama_host}. Is Ollama running? (ollama serve)"
        ) from exc

    model_names: List[str] = []
    models = listed.get("models") or []
    for m in models:
        name = m.get("model") or m.get("name") or ""
        if name:
            model_names.append(name.split(":")[0])

    target = settings.ollama_model.split(":")[0]
    if not any(n == target or n.startswith(f"{target}:") for n in model_names):
        raise RuntimeError(
            f"Model '{settings.ollama_model}' not found in Ollama. "
            f"Run: ollama pull {settings.ollama_model}"
        )


def build_context(
    results: List[Dict[str, Any]],
    max_chars: int,
) -> str:
    """Legacy simple context builder. Prefer build_tagged_context for better grounding."""
    parts: List[str] = []
    total = 0
    for r in results:
        text = r["text"]
        sep = 2 if parts else 0
        if total + sep + len(text) > max_chars:
            remaining = max_chars - total - sep
            if remaining > 0:
                parts.append(text[:remaining])
            break
        parts.append(text)
        total += sep + len(text)
    return "\n\n".join(parts)


def _extract_key_sentences(text: str, max_sentences: int = 4) -> str:
    """Very lightweight sentence extraction for compression (no extra models)."""
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    if len(sentences) <= max_sentences:
        return text.strip()
    # Prefer longer, information-dense sentences
    scored = sorted(sentences, key=lambda s: (len(s) > 60, len(s)), reverse=True)
    selected = scored[:max_sentences]
    # Preserve rough original order
    order = {s: i for i, s in enumerate(sentences)}
    selected.sort(key=lambda s: order.get(s, 999))
    return " ".join(selected)


def build_tagged_context(
    results: List[Dict[str, Any]],
    max_chars: int,
    compress: bool = True,
) -> str:
    """
    Build context with explicit [Source: ...] tags for citations.
    This is the recommended context builder for grounded answers.
    """
    parts: List[str] = []
    total = 0

    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        source = str(meta.get("source", meta.get("file_name", f"chunk-{i}")))
        chunk_idx = meta.get("chunk_index", i)

        raw_text = r["text"].strip()
        if compress and len(raw_text) > 400:
            text = _extract_key_sentences(raw_text)
        else:
            text = raw_text

        tagged = f"[Source: {source}#{chunk_idx}]\n{text}"

        sep = 2 if parts else 0
        if total + sep + len(tagged) > max_chars:
            remaining = max_chars - total - sep
            if remaining > 50:
                # Truncate but keep the tag
                tag = f"[Source: {source}#{chunk_idx}]\n"
                room = max(0, remaining - len(tag))
                parts.append(tag + text[:room])
            break

        parts.append(tagged)
        total += sep + len(tagged)

    return "\n\n".join(parts)


def generate_answer(
    prompt: str,
    history: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Generate an answer. Supports optional conversation history for multi-turn.
    history: list of (user_question, assistant_answer) pairs.
    """
    settings = get_settings()
    import ollama

    client = ollama.Client(host=settings.ollama_host)

    messages: List[Dict[str, str]] = []

    # System guidance for better behavior
    messages.append({
        "role": "system",
        "content": (
            "You are a helpful assistant with access to the user's personal knowledge base. "
            "Answer concisely. When using information from the provided context, cite the sources "
            "using the exact [Source: ...] labels that appear in the context. "
            "If the answer is not in the context, say so clearly."
        ),
    })

    if history:
        for user_q, assistant_a in history[-3:]:  # limit history to keep context small
            if user_q:
                messages.append({"role": "user", "content": user_q})
            if assistant_a:
                messages.append({"role": "assistant", "content": assistant_a})

    messages.append({"role": "user", "content": prompt})

    response = client.chat(
        model=settings.ollama_model,
        messages=messages,
        stream=False,
    )
    content = response["message"]["content"]
    return str(content)


def generate_answer_stream(
    prompt: str,
    history: Optional[List[Tuple[str, str]]] = None,
):
    """
    Streaming version of generate_answer. Yields tokens as they arrive from Ollama.
    Use this for much better perceived performance in CLI and UI.
    """
    settings = get_settings()
    import ollama

    client = ollama.Client(host=settings.ollama_host)

    messages: List[Dict[str, str]] = []

    messages.append({
        "role": "system",
        "content": (
            "You are a helpful assistant with access to the user's personal knowledge base. "
            "Answer concisely. When using information from the provided context, cite the sources "
            "using the exact [Source: ...] labels that appear in the context. "
            "If the answer is not in the context, say so clearly."
        ),
    })

    if history:
        for user_q, assistant_a in history[-3:]:
            if user_q:
                messages.append({"role": "user", "content": user_q})
            if assistant_a:
                messages.append({"role": "assistant", "content": assistant_a})

    messages.append({"role": "user", "content": prompt})

    stream = client.chat(
        model=settings.ollama_model,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def extract_citations(answer: str) -> List[str]:
    """
    Extract unique [Source: ...] citations from a generated answer.
    Returns them in order of first appearance.
    """
    if not answer:
        return []
    pattern = r"\[Source:\s*([^\]]+?)\]"
    matches = re.findall(pattern, answer)
    seen = set()
    ordered: List[str] = []
    for m in matches:
        m = m.strip()
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered
