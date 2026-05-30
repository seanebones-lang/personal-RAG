"""Sentence-transformer embeddings."""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import get_settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_model_name: str | None = None


def get_model() -> SentenceTransformer:
    global _model, _model_name
    settings = get_settings()
    if _model is None or _model_name != settings.embed_model:
        logger.info("Loading embedding model: %s", settings.embed_model)
        _model = SentenceTransformer(settings.embed_model, device="cpu")
        _model_name = settings.embed_model
    return _model


def reset_model() -> None:
    """Clear cached model (for tests)."""
    global _model, _model_name
    _model = None
    _model_name = None


def embed_texts(texts: List[str], show_progress: bool = True) -> np.ndarray:
    if not texts:
        return np.array([])
    model = get_model()
    return model.encode(
        texts,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    )


def embed_query(text: str) -> np.ndarray:
    model = get_model()
    result = model.encode([text], convert_to_numpy=True)[0]
    return np.asarray(result)
