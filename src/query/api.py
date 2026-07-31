"""REST API layer for PersonalRAGVault using FastAPI.

Local-first by design — bind to 127.0.0.1 by default via CLI `serve`.

Endpoints:
- GET  /health
- GET  /status
- POST /query
- POST /ingest
- GET  /cache/stats
- POST /cache/clear
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.core.vault import get_status_info, preview_ingest, run_ingest, run_query
from src.store.response_cache import get_response_cache, reset_response_cache

app = FastAPI(
    title="PersonalRAGVault API",
    version="1.3.0",
    description="Local personal RAG HTTP API. Do not expose beyond localhost without auth.",
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=50)
    max_distance: Optional[float] = None
    hybrid: bool = False
    use_llm: bool = True
    multi_query: bool = False
    expand_query: bool = False
    rerank: bool = False
    parent_expand: bool = False
    where_year: Optional[int] = None
    source_contains: Optional[str] = None
    extension: Optional[str] = None


class QueryResponse(BaseModel):
    results: list
    answer: Optional[str] = None
    context: Optional[str] = None
    llm_error: Optional[str] = None
    timings: Dict[str, Any]
    cached: bool = False


class IngestRequest(BaseModel):
    path: str
    recursive: bool = False
    force: bool = False
    allow_outside_home: bool = False
    dry_run: bool = False


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "personalragvault"}


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest) -> QueryResponse:
    try:
        from src.core.vault import build_where_from_options

        where = build_where_from_options(
            where_year=req.where_year,
            source_contains=req.source_contains,
            extension=req.extension,
        )
        result = run_query(
            req.question,
            top_k=req.top_k,
            max_distance=req.max_distance,
            where=where,
            hybrid=req.hybrid,
            use_llm=req.use_llm,
            multi_query=req.multi_query,
            expand_query=req.expand_query,
            rerank=req.rerank,
            parent_expand=req.parent_expand,
            stream=False,
        )
        return QueryResponse(
            results=result.get("results", []),
            answer=result.get("answer"),
            context=result.get("context"),
            llm_error=result.get("llm_error"),
            timings=result.get("timings") or {},
            cached=bool(result.get("cached")),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/ingest")
def ingest_endpoint(req: IngestRequest) -> Dict[str, Any]:
    try:
        path = Path(req.path).expanduser()
        if req.dry_run:
            return preview_ingest(
                path,
                recursive=req.recursive,
                allow_outside_home=req.allow_outside_home,
                force=req.force,
            )
        count = run_ingest(
            path,
            recursive=req.recursive,
            force=req.force,
            allow_outside_home=req.allow_outside_home,
            show_progress=False,
        )
        return {"ingested_chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/status")
def status_endpoint() -> Dict[str, Any]:
    try:
        status = get_status_info()
        data = status.__dict__.copy()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/cache/stats")
def cache_stats() -> Dict[str, int]:
    return get_response_cache().stats()


@app.post("/cache/clear")
def cache_clear() -> Dict[str, str]:
    reset_response_cache()
    return {"status": "cleared"}
