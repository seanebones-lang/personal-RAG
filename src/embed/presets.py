"""Embedding model presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class EmbedPreset:
    name: str
    model_id: str
    dimensions: int
    ram_note: str
    description: str


EMBED_PRESETS: Dict[str, EmbedPreset] = {
    "mini": EmbedPreset(
        name="mini",
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        dimensions=384,
        ram_note="~80 MB",
        description="Default. Fast on CPU, good general retrieval.",
    ),
    "bge-small": EmbedPreset(
        name="bge-small",
        model_id="BAAI/bge-small-en-v1.5",
        dimensions=384,
        ram_note="~130 MB",
        description="Stronger English retrieval; same vector size as mini.",
    ),
    "bge-base": EmbedPreset(
        name="bge-base",
        model_id="BAAI/bge-base-en-v1.5",
        dimensions=768,
        ram_note="~440 MB",
        description="Higher quality; requires purge + re-ingest from mini/bge-small.",
    ),
}


def resolve_embed_model(preset_or_model: Optional[str] = None) -> str:
    """Resolve preset name or return explicit model id from settings."""
    if not preset_or_model:
        from src.config import get_settings

        return get_settings().embed_model
    key = preset_or_model.strip().lower()
    if key in EMBED_PRESETS:
        return EMBED_PRESETS[key].model_id
    return preset_or_model


def preset_for_model(model_id: str) -> Optional[EmbedPreset]:
    for preset in EMBED_PRESETS.values():
        if preset.model_id == model_id:
            return preset
    return None
