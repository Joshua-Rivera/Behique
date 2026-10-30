"""REST routes. All behaviour lives in ``Service``."""

from __future__ import annotations

import hmac
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from behique.agent import AskUnavailable, AskUpstreamError
from behique.indexer import Busy
from behique.service import BadRequest, NotFound, Service


class SourceIn(BaseModel):
    name: str = ""
    path: str


class IndexIn(BaseModel):
    source_id: int | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(8, ge=1, le=50)
    mode: Literal["hybrid", "vector", "bm25"] = "hybrid"
    source_id: int | None = None
    ext: str | None = None
    path_prefix: str | None = None


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    allow_web: bool | None = None
    source_id: int | None = None


def get_service(request: Request) -> Service:
    return request.app.state.service


def require_api_key(request: Request) -> None:
    expected = request.app.state.service.settings.api_key
    if not expected:
        return
    supplied = request.headers.get("x-api-key", "")
    auth = request.headers.get("authorization", "")
    if not supplied and auth.lower().startswith("bearer "):
        supplied = auth[7:]
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "invalid or missing API key")


Svc = Annotated[Service, Depends(get_service)]

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@router.get("/health")
def health(svc: Svc):
    return svc.health()


@router.post("/sources", status_code=201)
def add_source(body: SourceIn, svc: Svc):
    return svc.add_source(body.name, body.path)


@router.get("/sources")
def list_sources(svc: Svc):
    return svc.list_sources()


@router.get("/mounts")
def list_mounts(svc: Svc):
    return svc.list_mounts()


@router.post("/index", status_code=202)
def start_index(svc: Svc, body: IndexIn | None = None):
    return svc.start_index(body.source_id if body else None)


@router.get("/index/status")
def index_status(svc: Svc):
    return svc.index_status()


@router.post("/search")
def search(body: SearchIn, svc: Svc):
    return svc.search(**body.model_dump())


@router.get("/files/{file_id}")
def read_file(svc: Svc, file_id: int, chunk_id: int | None = None, context: int = 1):
    return svc.read_file(file_id, chunk_id, context)


@router.post("/ask")
def ask(body: AskIn, svc: Svc):
    return svc.ask(body.question, body.allow_web, body.source_id)


def install(app: FastAPI) -> None:
    app.include_router(router)

    @app.exception_handler(BadRequest)
    async def _bad(_, exc: BadRequest):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(NotFound)
    async def _nf(_, exc: NotFound):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(Busy)
    async def _busy(_, exc: Busy):
        return JSONResponse({"detail": "an index run is already in progress"}, status_code=409)

    @app.exception_handler(AskUnavailable)
    async def _no_key(_, exc: AskUnavailable):
        return JSONResponse(
            {"detail": "/ask is disabled: set ANTHROPIC_API_KEY to enable it"}, status_code=503
        )

    @app.exception_handler(AskUpstreamError)
    async def _upstream(_, exc: AskUpstreamError):
        headers = {"retry-after": exc.retry_after} if exc.retry_after else None
        return JSONResponse({"detail": str(exc)}, status_code=exc.status, headers=headers)
