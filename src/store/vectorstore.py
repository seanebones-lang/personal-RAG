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
HNSW_CONFIGURED_KEY = "hnsw_configured"


def _hnsw_metadata() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "hnsw:space": "cosine",
        "hnsw:search_ef": settings.hnsw_search_ef,
        "hnsw:M": settings.hnsw_m,
    }


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
    coll_name = name or settings.collection_name
    try:
        coll = client.get_collection(coll_name)
        meta = dict(coll.metadata or {})
        if not meta.get(HNSW_CONFIGURED_KEY):
            # HNSW params are set only at collection creation; do not resend hnsw:space.
            try:
                coll.modify(metadata={HNSW_CONFIGURED_KEY: True})
            except ValueError:
                pass
        return coll
    except Exception:
        meta = _hnsw_metadata()
        meta[HNSW_CONFIGURED_KEY] = True
        return client.create_collection(name=coll_name, metadata=meta)


def get_collection_embed_dim() -> Optional[int]:
    coll = get_collection()
    meta = coll.metadata or {}
    val = meta.get(EMBED_DIM_KEY)
    return int(val) if val is not None else None


def set_collection_embed_dim(dim: int) -> None:
    coll = get_collection()
    meta = dict(coll.metadata or {})
    if meta.get(EMBED_DIM_KEY) == dim:
        return
    meta[EMBED_DIM_KEY] = dim
    # Preserve non-HNSW metadata; Chroma rejects changing hnsw:space after create.
    safe = {k: v for k, v in meta.items() if not str(k).startswith("hnsw:")}
    coll.modify(metadata=safe)


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
    from src.store.embedding_cache import reset_cache as reset_embed_cache
    from src.store.file_cache import reset_cache
    from src.store.fts import purge_fts

    settings = get_settings()
    client = get_client()
    try:
        client.delete_collection(settings.collection_name)
    except Exception:
        pass
    meta = _hnsw_metadata()
    meta[HNSW_CONFIGURED_KEY] = True
    client.create_collection(name=settings.collection_name, metadata=meta)
    purge_fts()
    reset_cache()
    reset_embed_cache()
    logger.info("Purged collection %s", settings.collection_name)


def fetch_corpus(
    where: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch documents for BM25; paginate when collection exceeds limit."""
    settings = get_settings()
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    max_fetch = limit if limit is not None else settings.hybrid_fetch_limit
    batch_size = 1000
    out: List[Dict[str, Any]] = []
    offset = 0

    while offset < total and len(out) < max_fetch:
        n = min(batch_size, max_fetch - len(out), total - offset)
        kwargs: Dict[str, Any] = {
            "include": ["documents", "metadatas"],
            "limit": n,
            "offset": offset,
        }
        if where:
            kwargs["where"] = where
        try:
            result = collection.get(**kwargs)
        except TypeError:
            result = collection.get(
                include=["documents", "metadatas"],
                limit=min(max_fetch, total),
                **({"where": where} if where else {}),
            )
            offset = total
        except Exception as exc:
            logger.warning("fetch_corpus batch failed at offset %s: %s", offset, exc)
            break

        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        if not ids:
            break
        for i, doc_id in enumerate(ids):
            out.append(
                {
                    "id": doc_id,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                }
            )
        offset += len(ids)
        if len(ids) < n:
            break

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


def get_sidecar_stats() -> Dict[str, int]:
    settings = get_settings()
    stats: Dict[str, int] = {"chunks": count_documents()}
    for name, path in (
        ("file_cache_bytes", settings.db_path.parent / "file_cache.db"),
        ("fts_bytes", settings.db_path.parent / "fts.db"),
        ("embedding_cache_bytes", settings.db_path.parent / "embedding_cache.db"),
    ):
        stats[name] = path.stat().st_size if path.exists() else 0
    return stats


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
