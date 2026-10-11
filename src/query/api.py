"""REST API layer for PersonalRAGVault using FastAPI.

Local-first by design — bind to 127.0.0.1 by default via CLI `serve`.

Endpoints:
- GET  /health   (no auth)
- GET  /version  (no auth)
- GET  /status
- POST /query
- POST /query/stream  (SSE token stream)
- POST /ingest
- GET  /cache/stats
- POST /cache/clear
- GET  /graph/neighbors
- GET  /presets

Optional auth: set non-empty ``PRV_API_TOKEN`` to require
``Authorization: Bearer <token>`` on all routes except /health and /version.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src import __version__
from src.core.vault import get_status_info, preview_ingest, run_ingest, run_query
from src.store.response_cache import get_response_cache, reset_response_cache

_PACKAGE_NAME = "personalragvault"
_FALLBACK_VERSION = __version__


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
    are always public. Token compare is constant-time.
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
    # Constant-time compare; pad to equal length only for compare_digest requirement
    # when lengths differ, still reject without leaking via early return timing of ==
    if len(provided) != len(token) or not secrets.compare_digest(provided, token):
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
    preset: Optional[str] = Field(
        default=None,
        description="Query quality preset: fast | balanced | quality",
    )


class QueryResponse(BaseModel):
    results: list
    answer: Optional[str] = None
    context: Optional[str] = None
    llm_error: Optional[str] = None
    timings: Dict[str, Any]
    cached: bool = False
    flags: Optional[Dict[str, Any]] = None


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


@app.get("/presets")
def presets_endpoint() -> Dict[str, Any]:
    from src.retrieval.presets import list_query_presets

    return {"presets": list_query_presets()}


def _run_query_from_request(req: QueryRequest, stream: bool = False) -> Dict[str, Any]:
    from src.core.vault import build_where_from_options

    where = build_where_from_options(
        where_year=req.where_year,
        source_contains=req.source_contains,
        extension=req.extension,
    )
    return run_query(
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
        stream=stream,
        preset=req.preset,
    )


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest) -> QueryResponse:
    try:
        result = _run_query_from_request(req, stream=False)
        return QueryResponse(
            results=result.get("results", []),
            answer=result.get("answer"),
            context=result.get("context"),
            llm_error=result.get("llm_error"),
            timings=result.get("timings") or {},
            cached=bool(result.get("cached")),
            flags=result.get("flags"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/query/stream")
def query_stream_endpoint(req: QueryRequest) -> StreamingResponse:
    """SSE stream: meta event, token events, done event.

    Events:
      data: {"type":"meta","results":[...],"timings":{...},"flags":{...}}
      data: {"type":"token","text":"..."}
      data: {"type":"done","answer":"..."}
      data: {"type":"error","detail":"..."}
    """

    def event_gen():
        try:
            result = _run_query_from_request(req, stream=bool(req.use_llm))
            meta = {
                "type": "meta",
                "results": result.get("results", []),
                "context": result.get("context"),
                "timings": result.get("timings") or {},
                "flags": result.get("flags"),
                "llm_error": result.get("llm_error"),
            }
            yield f"data: {json.dumps(meta, default=str)}\n\n"

            if result.get("llm_error"):
                yield f"data: {json.dumps({'type': 'error', 'detail': result['llm_error']})}\n\n"
                return

            stream_gen = result.get("answer_stream")
            full = ""
            if stream_gen is not None:
                for token in stream_gen:
                    full += token
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            else:
                full = result.get("answer") or ""
                if full:
                    yield f"data: {json.dumps({'type': 'token', 'text': full})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'answer': full})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/ingest")
def ingest_endpoint(req: IngestRequest) -> Dict[str, Any]:
    try:
        # Hardening: allow_outside_home over API requires explicit env opt-in
        allow = req.allow_outside_home
        if allow and not _env_bool("PRV_API_ALLOW_OUTSIDE_HOME", False):
            raise HTTPException(
                status_code=403,
                detail=(
                    "allow_outside_home rejected by API. "
                    "Set PRV_API_ALLOW_OUTSIDE_HOME=1 to enable."
                ),
            )
        path = Path(req.path).expanduser()
        if req.dry_run:
            return preview_ingest(
                path,
                recursive=req.recursive,
                allow_outside_home=allow,
                force=req.force,
            )
        count = run_ingest(
            path,
            recursive=req.recursive,
            force=req.force,
            allow_outside_home=allow,
            show_progress=False,
        )
        return {"ingested_chunks": count}
    except HTTPException:
        raise
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
