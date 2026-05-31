"""Diagnostics and health checks for PersonalRAGVault.

Run via: personalragvault doctor
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.config import get_settings
from src.embed.embedder import get_embedding_dimension
from src.store.vectorstore import get_collection_embed_dim


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    detail: Optional[str] = None


def _human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def check_embedding_dimension_consistency() -> CheckResult:
    """Critical check: stored collection dim must match current embedder dim."""
    try:
        current_dim = get_embedding_dimension()
        stored_dim = get_collection_embed_dim()
    except Exception as exc:
        return CheckResult(
            "Embedding dimension",
            ok=False,
            message="Could not determine embedding dimensions",
            detail=str(exc),
        )

    if stored_dim is None:
        return CheckResult(
            "Embedding dimension",
            ok=True,
            message="No vectors stored yet (safe to change model)",
        )

    if current_dim == stored_dim:
        return CheckResult(
            "Embedding dimension",
            ok=True,
            message=f"Consistent ({current_dim}D)",
        )

    return CheckResult(
        "Embedding dimension",
        ok=False,
        message=f"MISMATCH: current model = {current_dim}D, stored collection = {stored_dim}D",
        detail="Run 'personalragvault purge' then re-ingest your data with the new model. "
               "Different embedding models are not compatible.",
    )


def check_ollama_health() -> CheckResult:
    from src.ollama_client import check_ollama_model

    try:
        check_ollama_model()
        settings = get_settings()
        return CheckResult(
            "Ollama",
            ok=True,
            message=f"OK ({settings.ollama_model} @ {settings.ollama_host})",
        )
    except Exception as exc:
        return CheckResult(
            "Ollama",
            ok=False,
            message="Ollama check failed",
            detail=str(exc),
        )


def check_disk_space() -> CheckResult:
    settings = get_settings()
    db_path = settings.db_path
    try:
        usage = shutil.disk_usage(db_path.parent if db_path.exists() else Path.home())
        free = usage.free
        total = usage.total
        pct = (total - free) / total * 100 if total > 0 else 0

        if free < 1_000_000_000:  # < 1GB
            return CheckResult(
                "Disk space",
                ok=False,
                message=f"Very low free space: {_human_bytes(free)}",
                detail="Consider freeing space or moving PRV_DB_PATH",
            )
        return CheckResult(
            "Disk space",
            ok=True,
            message=f"{_human_bytes(free)} free ({pct:.1f}% used)",
        )
    except Exception as exc:
        return CheckResult("Disk space", ok=True, message="Could not check", detail=str(exc))


def check_caches() -> CheckResult:
    settings = get_settings()
    # Simplified: just report that caches are enabled
    msgs = []
    if settings.use_file_cache:
        msgs.append("file cache ON")
    if settings.use_embedding_cache:
        msgs.append("embedding cache ON")
    if settings.use_fts:
        msgs.append("FTS ON")

    return CheckResult(
        "Caches & indexes",
        ok=True,
        message=", ".join(msgs) if msgs else "All caches disabled",
    )


def check_large_vault_recommendations(chunk_count: int) -> List[str]:
    tips: List[str] = []
    if chunk_count > 8000:
        tips.append(
            "Large vault detected (>8k chunks). "
            "Consider enabling --hybrid and running 'personalragvault compact' regularly."
        )
    if chunk_count > 25000:
        tips.append(
            "Very large vault. You may benefit from --rerank with a fast reranker "
            "and tighter metadata filters."
        )
    return tips


def run_full_diagnostics(chunk_count: int = 0) -> List[CheckResult]:
    results: List[CheckResult] = []

    results.append(check_embedding_dimension_consistency())
    results.append(check_ollama_health())
    results.append(check_disk_space())
    results.append(check_caches())

    return results
