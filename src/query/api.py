"""REST API layer for PersonalRAGVault using FastAPI.

Local-first by design — bind to 127.0.0.1 by default via CLI `serve`.

Endpoints:
- GET  /health   (no auth)
- GET  /version  (no auth)
- GET  /status
- POST /query
- POST /ingest
- GET  /cache/stats
- POST /cache/clear
- GET  /graph/neighbors

Optional auth: set non-empty ``PRV_API_TOKEN`` to require
``Authorization: Bearer <token>`` on all routes except /health and /version.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src.core.vault import get_status_info, preview_ingest, run_ingest, run_query
from src.store.response_cache import get_response_cache, reset_response_cache

_PACKAGE_NAME = "personalragvault"
_FALLBACK_VERSION = "1.4.1"


def get_package_version() -> str:
    """Return installed package version, or fallback when not installed."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version(_PACKAGE_NAME)
        except PackageNotFoundError:
            return _FALLBACK_VERSION
    except Exception:
        return _FALLBACK_VERSION


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _default_hybrid() -> bool:
    """Query hybrid default from PRV_HYBRID without importing settings."""
    return _env_bool("PRV_HYBRID", default=False)


def require_api_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> None:
    """Optional bearer guard. Reads PRV_API_TOKEN each request (no reload).

    When unset or empty, auth is disabled (local-first). /health and /version
    are always public.
    """
    path = request.url.path
    if path in ("/health", "/version"):
        return
    token = (os.environ.get("PRV_API_TOKEN") or "").strip()
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    provided = authorization[7:].strip()
    if provided != token:
        raise HTTPException(
            status_code=401,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


_VERSION = get_package_version()

app = FastAPI(
    title="PersonalRAGVault API",
    version=_VERSION,
    description=(
        "Local-first personal RAG HTTP API. "
        "Default bind is localhost only — do not expose beyond the loopback "
        "without setting PRV_API_TOKEN (Bearer) and understanding vault risk. "
        "OpenAPI UI: /docs · ReDoc: /redoc"
    ),
    dependencies=[Depends(require_api_token)],
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=50)
    max_distance: Optional[float] = None
    hybrid: bool = Field(default_factory=_default_hybrid)
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


@app.get("/version")
def version_endpoint() -> Dict[str, str]:
    return {"version": get_package_version()}


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


@app.get("/graph/neighbors")
def graph_neighbors(
    note: str,
    direction: str = "both",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Wikilink neighbors for a note stem (same data as CLI `graph`)."""
    try:
        from src.retrieval.graph import neighbors

        d = (direction or "both").strip().lower()
        if d not in ("out", "in", "both"):
            raise HTTPException(status_code=422, detail="direction must be out, in, or both")
        return neighbors(note, direction=d, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
