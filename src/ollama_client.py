"""Ollama generation helpers."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


def _provider() -> str:
    return get_settings().llm_provider


def _openai_chat(
    messages: List[Dict[str, str]],
    timeout: float = 180.0,
) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint (e.g. NVIDIA NIM).

    Used when llm_provider == 'openai'. Non-streaming: returns the full response
    content string. For streaming use _openai_chat_stream.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "No API key for OpenAI-compatible provider. "
            "Set PRV_OPENAI_API_KEY or NVIDIA_API_KEY."
        )
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "stream": False,
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"OpenAI-compatible endpoint error {resp.status_code}: {resp.text[:300]}"
        )
    parsed = resp.json()
    return str(parsed["choices"][0]["message"]["content"])


def _openai_chat_stream(
    messages: List[Dict[str, str]],
    timeout: float = 180.0,
):
    """Streaming OpenAI-compatible chat. Yields text chunks as they arrive."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "No API key for OpenAI-compatible provider. "
            "Set PRV_OPENAI_API_KEY or NVIDIA_API_KEY."
        )
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "stream": True,
    }

    with httpx.stream(
        "POST",
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
    ) as resp:
        if resp.status_code >= 400:
            body = resp.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(
                f"OpenAI-compatible endpoint error {resp.status_code}: {body}"
            )
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[len("data: "):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content


def check_ollama_model() -> None:
    """Raise RuntimeError if the configured LLM provider/model is unavailable.

    For the default 'openai' provider this only asserts a key is present (the
    endpoint is validated on first chat). For 'ollama' it checks the local
    server and model (legacy path).
    """
    settings = get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "No API key for OpenAI-compatible provider. "
                "Set PRV_OPENAI_API_KEY or NVIDIA_API_KEY."
            )
        return

    # Legacy local Ollama path
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


def _query_terms(query: Optional[str]) -> set[str]:
    if not query:
        return set()
    stop = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "when",
        "where",
        "who",
        "how",
        "why",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "my",
        "me",
        "i",
        "do",
        "does",
        "did",
        "with",
        "from",
        "about",
    }
    return {
        w
        for w in re.findall(r"[A-Za-z0-9_]{3,}", query.lower())
        if w not in stop
    }


def _extract_key_sentences(
    text: str,
    max_sentences: int = 4,
    query: Optional[str] = None,
) -> str:
    """Lightweight sentence extraction; prefers query-term overlap when query given."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    if len(sentences) <= max_sentences:
        return text.strip()

    terms = _query_terms(query)

    def score(s: str) -> tuple:
        lower = s.lower()
        overlap = sum(1 for t in terms if t in lower) if terms else 0
        # Prefer relevance, then moderate length (info density without giant dumps)
        length_bonus = 1 if 40 <= len(s) <= 280 else 0
        return (overlap, length_bonus, min(len(s), 400))

    scored = sorted(sentences, key=score, reverse=True)
    selected = scored[:max_sentences]
    order = {s: i for i, s in enumerate(sentences)}
    selected.sort(key=lambda s: order.get(s, 999))
    return " ".join(selected)


def build_tagged_context(
    results: List[Dict[str, Any]],
    max_chars: int,
    compress: bool = True,
    query: Optional[str] = None,
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
            text = _extract_key_sentences(raw_text, query=query)
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

    if settings.llm_provider == "openai":
        return _openai_chat(messages)

    import ollama

    client = ollama.Client(host=settings.ollama_host)

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

    if settings.llm_provider == "openai":
        yield from _openai_chat_stream(messages)
        return

    import ollama

    client = ollama.Client(host=settings.ollama_host)

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
