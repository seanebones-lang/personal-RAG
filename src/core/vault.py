"""Vault operations used by CLI and UI."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.config import get_settings
from src.embed.embedder import (
    embed_query,
    embed_texts,
    ensure_embedding_compatible,
    get_embedding_dimension,
)
from src.embed.presets import EMBED_PRESETS, preset_for_model
from src.filters import build_where
from src.ingest.pipeline import build_documents_from_folder, iter_file_documents
from src.ollama_client import (
    build_tagged_context,
    check_ollama_model,
    generate_answer,
    generate_answer_stream,
)
from src.retrieval.hybrid import hybrid_search
from src.retrieval.multi_query import (
    expand_queries_heuristic,
    expand_queries_ollama,
    multi_query_search,
)
from src.retrieval.parent import expand_parent_chunks
from src.retrieval.rerank import rerank_results
from src.store.response_cache import get_response_cache, reset_response_cache
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

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, int, int, Dict[str, Any]], None]]


@dataclass
class StatusInfo:
    chunk_count: int
    db_path: str
    embed_model: str
    embed_dim: Optional[int]
    embed_preset: Optional[str]
    ollama_host: str
    ollama_model: str
    generation_provider: str
    generation_endpoint: str
    generation_model: str
    chunk_size: int
    chunk_overlap: int
    use_file_cache: bool
    use_fts: bool
    use_embedding_cache: bool
    chunk_strategy: str
    hnsw_search_ef: int
    sidecar_stats: Dict[str, int]
    response_cache_enabled: bool = False
    response_cache_stats: Optional[Dict[str, int]] = None
    hybrid_default: bool = False
    ingest_exclude_dir_count: int = 0


def get_status_info() -> StatusInfo:
    settings = get_settings()
    preset = preset_for_model(settings.embed_model)
    dim = get_collection_embed_dim()
    cache_stats = None
    if settings.response_cache_enabled:
        cache_stats = get_response_cache().stats()
    return StatusInfo(
        chunk_count=count_documents(),
        db_path=str(settings.db_path),
        embed_model=settings.embed_model,
        embed_dim=dim,
        embed_preset=preset.name if preset else None,
        ollama_host=settings.ollama_host,
        ollama_model=settings.ollama_model,
        generation_provider=settings.llm_provider,
        generation_endpoint=(
            settings.openai_base_url if settings.llm_provider == "openai" else settings.ollama_host
        ),
        generation_model=(
            settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model
        ),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        use_file_cache=settings.use_file_cache,
        use_fts=settings.use_fts,
        use_embedding_cache=settings.use_embedding_cache,
        chunk_strategy=settings.chunk_strategy,
        hnsw_search_ef=settings.hnsw_search_ef,
        sidecar_stats=get_sidecar_stats(),
        response_cache_enabled=settings.response_cache_enabled,
        response_cache_stats=cache_stats,
        hybrid_default=settings.hybrid_default,
        ingest_exclude_dir_count=len(settings.ingest_exclude_dirs),
    )


def preview_ingest(
    path: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Dry-run ingest: count files/chunks without embedding or writing."""
    from src.ingest.ingest import discover_files, validate_ingest_path
    from src.store.file_cache import should_skip_file

    validated = validate_ingest_path(path, allow_outside_home=allow_outside_home)
    files = discover_files(validated, recursive=recursive)
    would_process = 0
    would_skip = 0
    estimated_chunks = 0
    sample: List[str] = []

    for file_path in files:
        if should_skip_file(file_path, force=force):
            would_skip += 1
            continue
        would_process += 1
        if len(sample) < 12:
            sample.append(str(file_path))
        # Cheap estimate: ~chars/chunk_size without full parse cost for huge trees
        try:
            size = file_path.stat().st_size
            settings = get_settings()
            # rough text ratio + chunk_size
            est = max(1, int((size * 0.6) / max(settings.chunk_size, 1)))
            estimated_chunks += min(est, 5000)
        except OSError:
            estimated_chunks += 1

    return {
        "files_discovered": len(files),
        "files_to_process": would_process,
        "files_unchanged_skip": would_skip,
        "estimated_chunks": estimated_chunks,
        "sample_paths": sample,
    }


def run_ingest(
    path: Path,
    recursive: bool = False,
    allow_outside_home: bool = False,
    force: bool = False,
    show_progress: bool = True,
    chunk_strategy: Optional[str] = None,
    progress_callback: ProgressCallback = None,
    batch_size: Optional[int] = None,
) -> int:
    """Ingest folder with optional streaming batch upsert (large vault safe)."""
    from src.config import normalize_chunk_strategy
    from src.ingest.chunking.context import (
        reset_chunk_strategy_override,
        set_chunk_strategy_override,
    )

    ensure_embedding_compatible()
    settings = get_settings()
    batch = batch_size if batch_size is not None else settings.ingest_batch_size

    token = None
    if chunk_strategy:
        token = set_chunk_strategy_override(normalize_chunk_strategy(chunk_strategy))

    total_chunks = 0
    pending: List[Dict[str, Any]] = []
    files_done = 0
    files_total = 0

    try:
        # Prefer streaming path for memory control
        for file_path, file_docs, meta in iter_file_documents(
            path,
            recursive=recursive,
            allow_outside_home=allow_outside_home,
            force_reingest=force,
        ):
            files_total = meta.get("files_total", files_total)
            files_done += 1
            if progress_callback:
                progress_callback(
                    "file",
                    files_done,
                    max(files_total, files_done),
                    {
                        "path": str(file_path),
                        "chunks": len(file_docs),
                        "skipped": meta.get("skipped", False),
                    },
                )
            if not file_docs:
                continue

            sources = list({str(d["metadata"]["source"]) for d in file_docs})
            delete_by_sources(sources)
            pending.extend(file_docs)

            while len(pending) >= batch:
                chunk = pending[:batch]
                del pending[:batch]
                _attach_embeddings(chunk, show_progress=show_progress and not progress_callback)
                upsert_documents(chunk)
                total_chunks += len(chunk)
                if progress_callback:
                    progress_callback(
                        "embed_upsert",
                        total_chunks,
                        total_chunks + len(pending),
                        {"batch": len(chunk)},
                    )

        if pending:
            _attach_embeddings(pending, show_progress=show_progress and not progress_callback)
            upsert_documents(pending)
            total_chunks += len(pending)
            if progress_callback:
                progress_callback(
                    "embed_upsert",
                    total_chunks,
                    total_chunks,
                    {"batch": len(pending), "final": True},
                )
    finally:
        if token is not None:
            reset_chunk_strategy_override(token)

    if total_chunks:
        set_collection_embed_dim(get_embedding_dimension())
        # Invalidate response cache after vault mutation
        if settings.response_cache_enabled:
            reset_response_cache()
    return total_chunks


def run_query(
    question: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    where: Optional[Dict[str, Any]] = None,
    hybrid: bool = False,
    use_llm: bool = True,
    multi_query: bool = False,
    expand_query: bool = False,
    rerank: bool = False,
    parent_expand: bool = False,
    history: Optional[List[Tuple[str, str]]] = None,
    stream: bool = False,
    preset: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve (+ optional LLM answer). Caches non-stream results when enabled.

    ``hybrid`` defaults to False for backward compatibility. CLI/API/UI callers
    should pass ``hybrid=get_settings().hybrid_default`` (from ``PRV_HYBRID``)
    when the user has not explicitly overridden the flag.

    ``preset`` may be ``fast`` / ``balanced`` / ``quality`` (see retrieval.presets).
    """
    settings = get_settings()

    # Streaming and multi-turn history: never cache
    if stream or history:
        return _run_query_impl(
            question,
            top_k=top_k,
            max_distance=max_distance,
            where=where,
            hybrid=hybrid,
            use_llm=use_llm,
            multi_query=multi_query,
            expand_query=expand_query,
            rerank=rerank,
            parent_expand=parent_expand,
            history=history,
            stream=stream,
            preset=preset,
        )

    if not settings.response_cache_enabled:
        return _run_query_impl(
            question,
            top_k=top_k,
            max_distance=max_distance,
            where=where,
            hybrid=hybrid,
            use_llm=use_llm,
            multi_query=multi_query,
            expand_query=expand_query,
            rerank=rerank,
            parent_expand=parent_expand,
            history=history,
            stream=stream,
            preset=preset,
        )

    cache = get_response_cache()
    key_kwargs = {
        "top_k": top_k,
        "max_distance": max_distance,
        "hybrid": hybrid,
        "use_llm": use_llm,
        "multi": multi_query,
        "expand": expand_query,
        "rerank": rerank,
        "parent": parent_expand,
        "where": where,
        "preset": preset,
    }
    cached = cache.get(question, **key_kwargs)
    if cached is not None:
        out = dict(cached)
        out["cached"] = True
        return out

    result = _run_query_impl(
        question,
        top_k=top_k,
        max_distance=max_distance,
        where=where,
        hybrid=hybrid,
        use_llm=use_llm,
        multi_query=multi_query,
        expand_query=expand_query,
        rerank=rerank,
        parent_expand=parent_expand,
        history=history,
        stream=stream,
        preset=preset,
    )
    # Do not cache generators or errors that might be transient
    if result.get("answer_stream") is None and result.get("llm_error") is None:
        to_store = {k: v for k, v in result.items() if k != "answer_stream"}
        cache.set(question, to_store, **key_kwargs)
    result["cached"] = False
    return result


def _run_query_impl(
    question: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    where: Optional[Dict[str, Any]] = None,
    hybrid: bool = False,
    use_llm: bool = True,
    multi_query: bool = False,
    expand_query: bool = False,
    rerank: bool = False,
    parent_expand: bool = False,
    history: Optional[List[Tuple[str, str]]] = None,
    stream: bool = False,
    preset: Optional[str] = None,
) -> Dict[str, Any]:
    settings = get_settings()

    # Apply query preset (explicit flags still win when already True via args/env)
    from src.retrieval.presets import resolve_query_preset

    qp = resolve_query_preset(preset or getattr(settings, "query_preset", None))
    if qp is not None:
        hybrid = hybrid or qp.hybrid
        multi_query = multi_query or qp.multi_query
        expand_query = expand_query or qp.expand_query
        rerank = rerank or qp.rerank
        parent_expand = parent_expand or qp.parent_expand

    use_multi = multi_query or settings.multi_query
    # Retrieval-only mode also forbids generation requests for query expansion.
    use_expand = use_llm and (expand_query or settings.expand_query_ollama)
    use_rerank = rerank or settings.rerank
    use_parent = parent_expand or settings.parent_expand
    # hybrid stays as passed (CLI already applied hybrid_default); preset may force on
    use_hybrid = bool(hybrid)

    t0 = time.perf_counter()

    def _vector_search(emb, k: int) -> List[Dict[str, Any]]:
        return search(emb, top_k=k, max_distance=max_distance, where=where)

    candidate_k = settings.rerank_candidates if use_rerank else top_k

    if use_multi:
        if use_expand:
            try:
                queries = expand_queries_ollama(question)
            except Exception:
                queries = expand_queries_heuristic(question)
        else:
            queries = expand_queries_heuristic(question)
        results = multi_query_search(
            queries,
            search_fn=_vector_search,
            embed_fn=embed_query,
            top_k=candidate_k,
            rrf_k=settings.hybrid_rrf_k,
            hybrid=use_hybrid,
            vector_search_fn=search if use_hybrid else None,
            fetch_corpus_fn=fetch_corpus if use_hybrid else None,
            where=where,
            max_distance=max_distance,
        )
    elif use_hybrid:
        query_embedding = embed_query(question)
        results = hybrid_search(
            query_text=question,
            query_embedding=query_embedding,
            vector_search_fn=search,
            fetch_corpus_fn=fetch_corpus,
            top_k=candidate_k,
            where=where,
            max_distance=max_distance,
        )
    else:
        query_embedding = embed_query(question)
        results = search(
            query_embedding,
            top_k=candidate_k,
            max_distance=max_distance,
            where=where,
        )

    if use_rerank and results:
        results = rerank_results(question, results, top_k, model_name=settings.rerank_model)
    elif len(results) > top_k:
        results = results[:top_k]

    if use_parent:
        results = expand_parent_chunks(results)

    retrieval_time = time.perf_counter() - t0

    context = build_tagged_context(
        results,
        settings.max_context_chars,
        compress=True,
        query=question,
    )

    answer = None
    llm_error = None
    generation_time = 0.0
    answer_stream = None

    if use_llm and results:
        try:
            check_ollama_model()
            prompt = (
                "Use the following context from the user's personal knowledge base "
                "to answer the question.\nCite sources using the exact [Source: ...] "
                "labels shown.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {question}\n\n"
                "Answer:"
            )

            if stream:
                answer_stream = generate_answer_stream(prompt, history=history)
            else:
                t_gen = time.perf_counter()
                answer = generate_answer(prompt, history=history)
                generation_time = time.perf_counter() - t_gen
        except Exception as exc:
            llm_error = str(exc)

    total_time = time.perf_counter() - t0

    return {
        "results": results,
        "context": context,
        "answer": answer,
        "llm_error": llm_error,
        "answer_stream": answer_stream,
        "timings": {
            "retrieval": round(retrieval_time, 3),
            "generation": round(generation_time, 3) if generation_time > 0 else None,
            "total": round(total_time, 3),
        },
        "cached": False,
        "flags": {
            "hybrid": use_hybrid,
            "multi_query": use_multi,
            "rerank": use_rerank,
            "parent_expand": use_parent,
            "preset": qp.name if qp else None,
        },
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
    reset_response_cache()


def run_compact() -> Dict[str, int]:
    return compact_maintenance()


def highlight_excerpt(full_text: str, excerpt: str, max_excerpt: int = 500) -> str:
    """Wrap first matching excerpt in markdown bold for UI preview."""
    if not excerpt or not full_text:
        return full_text
    needle = excerpt[:max_excerpt].strip()
    if len(needle) < 10:
        return full_text
    idx = full_text.find(needle)
    if idx < 0:
        short = needle[:80]
        idx = full_text.find(short)
        if idx < 0:
            return full_text
        needle = short
    before = full_text[:idx]
    after = full_text[idx + len(needle) :]
    return f"{before}**{needle}**{after}"


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


# Keep build_documents_from_folder import used by tests/scripts that monkeypatch vault
__all__ = [
    "StatusInfo",
    "get_status_info",
    "preview_ingest",
    "run_ingest",
    "run_query",
    "run_purge",
    "run_compact",
    "highlight_excerpt",
    "preview_source",
    "build_where_from_options",
    "list_embed_presets",
    "build_documents_from_folder",
]
