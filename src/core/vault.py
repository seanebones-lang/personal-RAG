"""Vault operations used by CLI and UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.embed.embedder import (
    embed_query,
    embed_texts,
    ensure_embedding_compatible,
    get_embedding_dimension,
)
from src.embed.presets import EMBED_PRESETS, preset_for_model
from src.filters import build_where
from src.ingest.pipeline import build_documents_from_folder
from src.ollama_client import build_context, check_ollama_model, generate_answer
from src.retrieval.hybrid import hybrid_search
from src.store.vectorstore import (
    compact_maintenance,
    count_documents,
    delete_by_sources,
    fetch_corpus,
    get_collection_embed_dim,
    get_sidecar_stats,
    purge_collection,
    search,
    set_collection_embed_dim,
    upsert_documents,
)


@dataclass
class StatusInfo:
    chunk_count: int
    db_path: str
    embed_model: str
    embed_dim: Optional[int]
    embed_preset: Optional[str]
    ollama_host: str
    ollama_model: str
    chunk_size: int
    chunk_overlap: int
    use_file_cache: bool
    use_fts: bool
    use_embedding_cache: bool
    chunk_strategy: str
    hnsw_search_ef: int
    sidecar_stats: Dict[str, int]


def get_status_info() -> StatusInfo:
    settings = get_settings()
    preset = preset_for_model(settings.embed_model)
    dim = get_collection_embed_dim()
    return StatusInfo(
        chunk_count=count_documents(),
        db_path=str(settings.db_path),
        embed_model=settings.embed_model,
        embed_dim=dim,
        embed_preset=preset.name if preset else None,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        use_file_cache=settings.use_file_cache,
        use_fts=settings.use_fts,
        use_embedding_cache=settings.use_embedding_cache,
        chunk_strategy=settings.chunk_strategy,
        hnsw_search_ef=settings.hnsw_search_ef,
        sidecar_stats=get_sidecar_stats(),
    )


def run_ingest(
    path: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force: bool = False,
    show_progress: bool = True,
) -> int:
    ensure_embedding_compatible()
    docs = build_documents_from_folder(
        path,
        recursive=recursive,
        allow_outside_home=allow_outside_home,
        force_reingest=force,
    )
    if not docs:
        return 0

    sources = list({str(d["metadata"]["source"]) for d in docs})
    delete_by_sources(sources)

    _attach_embeddings(docs, show_progress=show_progress)

    upsert_documents(docs)
    set_collection_embed_dim(get_embedding_dimension())
    return len(docs)


def run_query(
    question: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    where: Optional[Dict[str, Any]] = None,
    hybrid: bool = False,
    use_llm: bool = True,
) -> Dict[str, Any]:
    settings = get_settings()
    query_embedding = embed_query(question)

    if hybrid:
        results = hybrid_search(
            query_text=question,
            query_embedding=query_embedding,
            vector_search_fn=search,
            fetch_corpus_fn=fetch_corpus,
            top_k=top_k,
            where=where,
            max_distance=max_distance,
        )
    else:
        results = search(
            query_embedding,
            top_k=top_k,
            max_distance=max_distance,
            where=where,
        )

    context = build_context(results, settings.max_context_chars)
    answer = None
    llm_error = None
    if use_llm and results:
        try:
            check_ollama_model()
            prompt = (
                "You are a helpful assistant with access to the user's "
                "personal knowledge base.\n"
                "Use the following context to answer the question. "
                "If the answer is not in the context, say so.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {question}\n\n"
                "Answer:"
            )
            answer = generate_answer(prompt)
        except Exception as exc:
            llm_error = str(exc)

    return {
        "results": results,
        "context": context,
        "answer": answer,
        "llm_error": llm_error,
    }


def _attach_embeddings(docs: List[Dict[str, Any]], show_progress: bool = True) -> None:
    from src.store.embedding_cache import get_cached, store_cached, text_hash

    embeddings: List[Any] = [None] * len(docs)
    pending_texts: List[str] = []
    pending_indices: List[int] = []

    for i, doc in enumerate(docs):
        th = text_hash(doc["text"])
        cached = get_cached(doc["id"], th)
        if cached is not None:
            embeddings[i] = cached
        else:
            pending_texts.append(doc["text"])
            pending_indices.append(i)

    if pending_texts:
        encoded = embed_texts(pending_texts, show_progress=show_progress)
        for j, idx in enumerate(pending_indices):
            embeddings[idx] = encoded[j]
            doc = docs[idx]
            store_cached(doc["id"], text_hash(doc["text"]), encoded[j])

    for i, doc in enumerate(docs):
        doc["embedding"] = embeddings[i]


def run_purge() -> None:
    purge_collection()


def run_compact() -> Dict[str, int]:
    return compact_maintenance()


def preview_source(source_path: str, max_chars: int = 4000) -> str:
    """Read a safe preview of an ingested source file."""
    path = Path(source_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return f"File not found: {path}"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            if not reader.pages:
                return "(empty PDF)"
            text = reader.pages[0].extract_text() or ""
            return text[:max_chars] + ("..." if len(text) > max_chars else "")
        except Exception as exc:
            return f"Could not read PDF: {exc}"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception as exc:
        return f"Could not read file: {exc}"


def build_where_from_options(
    where_year: Optional[int] = None,
    source_contains: Optional[str] = None,
    extension: Optional[str] = None,
    filter_json: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    return build_where(
        where_year=where_year,
        source_contains=source_contains,
        extension=extension,
        filter_json=filter_json,
    )


def list_embed_presets() -> List[Dict[str, Any]]:
    return [
        {
            "name": p.name,
            "model_id": p.model_id,
            "dimensions": p.dimensions,
            "ram_note": p.ram_note,
            "description": p.description,
        }
        for p in EMBED_PRESETS.values()
    ]
