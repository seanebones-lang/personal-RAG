"""REST API layer for PersonalRAGVault using FastAPI.

Endpoints:
- POST /query
- POST /ingest
- GET /status
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.core.vault import get_status_info, run_ingest, run_query
from src.store.response_cache import get_response_cache

app = FastAPI(title="PersonalRAGVault API", version="1.3.0")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 8
    multi_query: bool = False
    rerank: bool = False


class QueryResponse(BaseModel):
    results: list
    answer: Optional[str] = None
    timings: Dict[str, Any]
    cached: bool = False


class IngestRequest(BaseModel):
    path: str
    recursive: bool = False
    force: bool = False


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    try:
        result = run_query(
            req.question,
            top_k=req.top_k,
            multi_query=req.multi_query,
            rerank=req.rerank,
        )
        cache = get_response_cache()
        stats = cache.stats()
        return QueryResponse(
            results=result.get("results", []),
            answer=result.get("answer"),
            timings=result.get("timings", {}),
            cached=stats["hits"] > 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
def ingest_endpoint(req: IngestRequest):
    try:
        count = run_ingest(req.path, recursive=req.recursive, force=req.force)
        return {"ingested_chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
def status_endpoint():
    try:
        status = get_status_info()
        return status.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/stats")
def cache_stats():
    return get_response_cache().stats()
