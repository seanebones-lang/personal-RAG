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


def get_embedding_dimension() -> int:
    dim = get_model().get_sentence_embedding_dimension()
    if dim is None:
        raise RuntimeError("Could not determine embedding dimension from model")
    return int(dim)


def ensure_embedding_compatible() -> None:
    """Raise if existing collection embedding dimension mismatches current model."""
    from src.store.vectorstore import get_collection_embed_dim, set_collection_embed_dim

    current = get_embedding_dimension()
    stored = get_collection_embed_dim()
    if stored is not None and stored != current:
        raise ValueError(
            f"Embedding dimension mismatch: vault has {stored}d but model "
            f"produces {current}d. Run: personalragvault purge --yes "
            f"then re-ingest, or set PRV_EMBED_MODEL to the original model."
        )
    if stored is None:
        set_collection_embed_dim(current)


def embed_texts(texts: List[str], show_progress: bool = True) -> np.ndarray:
    if not texts:
        return np.array([])
    settings = get_settings()
    model = get_model()
    batch_size = settings.embed_batch_size
    if len(texts) <= batch_size:
        return model.encode(
            texts,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
    parts: List[np.ndarray] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        parts.append(
            model.encode(
                batch,
                show_progress_bar=show_progress and i == 0,
                convert_to_numpy=True,
            )
        )
    return np.vstack(parts)


def embed_query(text: str) -> np.ndarray:
    model = get_model()
    result = model.encode([text], convert_to_numpy=True)[0]
    return np.asarray(result)
