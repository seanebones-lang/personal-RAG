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
EMBED_DIM_KEY = "embed_dim"


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


def get_collection_embed_dim() -> Optional[int]:
    coll = get_collection()
    meta = coll.metadata or {}
    val = meta.get(EMBED_DIM_KEY)
    return int(val) if val is not None else None


def set_collection_embed_dim(dim: int) -> None:
    coll = get_collection()
    meta = dict(coll.metadata or {})
    meta[EMBED_DIM_KEY] = dim
    coll.modify(metadata=meta)


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
    from src.store.fts import index_chunks

    if get_settings().use_fts:
        index_chunks(
            [
                (d["id"], str(d.get("metadata", {}).get("source", "")), d["text"])
                for d in docs
            ]
        )
    logger.info("Upserted %d chunks into vector store", len(docs))
    return len(docs)


def delete_by_sources(sources: List[str]) -> int:
    """Remove all chunks whose metadata source is in sources."""
    if not sources:
        return 0
    from src.store.file_cache import remove_sources
    from src.store.fts import delete_by_sources as fts_delete

    collection = get_collection()
    removed = 0
    for source in sources:
        try:
            collection.delete(where={"source": source})
            removed += 1
        except Exception as exc:
            logger.warning("Could not delete source %s: %s", source, exc)
    fts_delete(sources)
    remove_sources(sources)
    return removed


def purge_collection() -> None:
    from src.store.file_cache import reset_cache
    from src.store.fts import purge_fts

    settings = get_settings()
    client = get_client()
    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    client.get_or_create_collection(name=settings.collection_name)
    purge_fts()
    reset_cache()
    logger.info("Purged collection %s", settings.collection_name)


def fetch_corpus(
    where: Optional[Dict[str, Any]] = None,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []
    n = min(limit, total)
    kwargs: Dict[str, Any] = {"include": ["documents", "metadatas"]}
    if where:
        kwargs["where"] = where
    try:
        result = collection.get(limit=n, **kwargs)
    except Exception as exc:
        logger.warning("fetch_corpus failed: %s", exc)
        return []

    out: List[Dict[str, Any]] = []
    ids = result.get("ids") or []
    docs = result.get("documents") or []
    metas = result.get("metadatas") or []
    for i, doc_id in enumerate(ids):
        out.append(
            {
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
            }
        )
    return out


def search(
    query_embedding: np.ndarray,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    n_results = min(top_k, total)
    query_kwargs: Dict[str, Any] = {
        "query_embeddings": [query_embedding.tolist()],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    ids = results["ids"][0]
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
                "id": ids[i],
                "text": docs[i],
                "metadata": metas[i] or {},
                "distance": distance,
            }
        )
    return out


def compact_maintenance() -> Dict[str, int]:
    """Remove orphaned file-cache entries; rebuild FTS from Chroma."""
    from src.store.file_cache import compact_orphans
    from src.store.fts import index_chunks, purge_fts

    corpus = fetch_corpus(limit=100_000)
    valid_sources = {str(c.get("metadata", {}).get("source", "")) for c in corpus}
    valid_sources.discard("")
    orphans = compact_orphans(valid_sources)

    if get_settings().use_fts:
        purge_fts()
        entries = [
            (c["id"], str(c.get("metadata", {}).get("source", "")), c["text"])
            for c in corpus
            if c.get("id")
        ]
        index_chunks(entries)

    return {"orphan_file_records": orphans, "fts_chunks_reindexed": len(corpus)}
