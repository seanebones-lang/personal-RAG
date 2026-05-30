"""ChromaDB persistent vector store."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
import numpy as np
from chromadb.config import Settings

from src.config import get_settings

logger = logging.getLogger(__name__)

_client: Any = None


def get_client() -> Any:
    global _client
    settings = get_settings()
    settings.db_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(settings.db_path),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def reset_client() -> None:
    """Clear cached client (for tests)."""
    global _client
    _client = None


def get_collection(name: Optional[str] = None):
    settings = get_settings()
    client = get_client()
    return client.get_or_create_collection(name=name or settings.collection_name)


def count_documents() -> int:
    return int(get_collection().count())


def upsert_documents(docs: List[Dict[str, Any]]) -> int:
    """docs: id, text, embedding, metadata."""
    if not docs:
        return 0
    collection = get_collection()
    collection.upsert(
        ids=[d["id"] for d in docs],
        embeddings=[d["embedding"].tolist() for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[d.get("metadata", {}) for d in docs],
    )
    logger.info("Upserted %d chunks into vector store", len(docs))
    return len(docs)


def delete_by_sources(sources: List[str]) -> int:
    """Remove all chunks whose metadata source is in sources."""
    if not sources:
        return 0
    collection = get_collection()
    removed = 0
    for source in sources:
        try:
            collection.delete(where={"source": source})
            removed += 1
        except Exception as exc:
            logger.warning("Could not delete source %s: %s", source, exc)
    return removed


def purge_collection() -> None:
    settings = get_settings()
    client = get_client()
    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    client.get_or_create_collection(name=settings.collection_name)
    logger.info("Purged collection %s", settings.collection_name)


def search(
    query_embedding: np.ndarray,
    top_k: int = 5,
    max_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    n_results = min(top_k, total)
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    out: List[Dict[str, Any]] = []
    for i in range(len(docs)):
        distance = dists[i]
        if max_distance is not None and distance > max_distance:
            continue
        out.append(
            {
                "text": docs[i],
                "metadata": metas[i] or {},
                "distance": distance,
            }
        )
    return out
