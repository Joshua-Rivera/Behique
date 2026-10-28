"""App factory: REST routes, MCP at /mcp, and the periodic rescan."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from behique import __version__, api
from behique.mcp_server import build_mcp
from behique.service import Service, build_service

log = logging.getLogger(__name__)


async def _rescan_loop(svc: Service) -> None:
    while True:
        await asyncio.sleep(svc.settings.rescan_seconds)
        if not svc.rescan():
            log.info("rescan skipped: index run in progress")


class _McpAuth:
    """Apply the same API-key rule as the REST routes to the mounted MCP app."""

    def __init__(self, inner, get_key) -> None:
        self.inner, self.get_key = inner, get_key

    async def __call__(self, scope, receive, send):
        key = self.get_key() if scope["type"] == "http" else None
        if key:
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            supplied = headers.get("x-api-key", "")
            auth = headers.get("authorization", "")
            if not supplied and auth.lower().startswith("bearer "):
                supplied = auth[7:]
            if not hmac.compare_digest(supplied.encode(), key.encode()):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"detail":"invalid or missing API key"}',
                    }
                )
                return
        await self.inner(scope, receive, send)


class _McpSlash:
    """Serve ``/mcp`` directly; a 307 to ``/mcp/`` breaks some MCP clients' POSTs."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/mcp":
            scope = {**scope, "path": "/mcp/", "raw_path": b"/mcp/"}
        await self.app(scope, receive, send)


def create_app(service: Service | None = None, *, rescan: bool = True) -> FastAPI:
    mcp = build_mcp(lambda: app.state.service)
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc = app.state.service = service or build_service()
        task = None
        async with mcp.session_manager.run():
            if rescan and svc.settings.rescan_seconds > 0:
                svc.rescan()  # index whatever is registered on startup
                task = asyncio.create_task(_rescan_loop(svc))
            try:
                yield
            finally:
                if task:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

    app = FastAPI(title="Behique", version=__version__, lifespan=lifespan)
    api.install(app)
    app.mount("/mcp", _McpAuth(mcp_app, lambda: app.state.service.settings.api_key))
    app.add_middleware(_McpSlash)
    return app


def app() -> FastAPI:  # uvicorn --factory behique.main:app
    logging.basicConfig(level=logging.INFO)
    return create_app()
