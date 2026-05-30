"""Ollama generation helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

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


def generate_answer(prompt: str) -> str:
    settings = get_settings()
    import ollama

    client = ollama.Client(host=settings.ollama_host)
    response = client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response["message"]["content"]
    return str(content)


def build_context(
    results: List[Dict[str, Any]],
    max_chars: int,
) -> str:
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
