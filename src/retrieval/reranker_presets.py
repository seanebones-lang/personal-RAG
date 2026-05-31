"""Reranker model presets for easy configuration.

These presets are designed with local/CPU usage in mind (especially Apple Silicon).

Usage:
    export PRV_RERANK_PRESET=mini
    export PRV_RERANK=true
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RerankerPreset:
    name: str
    model_id: str
    size_note: str
    description: str
    recommended_for: str


RERANKER_PRESETS: Dict[str, RerankerPreset] = {
    "tiny": RerankerPreset(
        name="tiny",
        model_id="cross-encoder/ms-marco-TinyBERT-L-2-v2",
        size_note="~4MB / very fast",
        description="Extremely lightweight TinyBERT reranker",
        recommended_for="Very large vaults or low-power devices where speed is critical",
    ),
    "mini": RerankerPreset(
        name="mini",
        model_id="cross-encoder/ms-marco-MiniLM-L-6-v2",
        size_note="~22MB / fast on CPU",
        description="Balanced MiniLM reranker (current default)",
        recommended_for="Most users — good quality/speed tradeoff",
    ),
    "bge": RerankerPreset(
        name="bge",
        model_id="BAAI/bge-reranker-base",
        size_note="~110MB / stronger quality",
        description="BGE reranker (stronger but heavier)",
        recommended_for="Users who want maximum reranking quality and have decent CPU/GPU",
    ),
}


def get_reranker_model(preset_name: Optional[str] = None) -> str:
    """Return the model ID for a given preset name (defaults to 'mini')."""
    if not preset_name:
        preset_name = "mini"
    preset_name = preset_name.lower().strip()
    if preset_name in RERANKER_PRESETS:
        return RERANKER_PRESETS[preset_name].model_id
    # Fallback: treat the value as a direct model ID
    return preset_name


def list_reranker_presets() -> list[dict]:
    """Return list of available reranker presets for CLI display."""
    return [
        {
            "name": p.name,
            "model_id": p.model_id,
            "size": p.size_note,
            "description": p.description,
            "recommended_for": p.recommended_for,
        }
        for p in RERANKER_PRESETS.values()
    ]


def resolve_reranker_model(preset_or_model: Optional[str]) -> str:
    """Resolve either a preset name or direct model ID to a model string."""
    if not preset_or_model:
        return RERANKER_PRESETS["mini"].model_id
    name = preset_or_model.lower().strip()
    if name in RERANKER_PRESETS:
        return RERANKER_PRESETS[name].model_id
    return preset_or_model  # Assume it's a direct HF model ID
