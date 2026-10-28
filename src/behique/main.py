"""App factory: REST routes, MCP at /mcp, and the periodic rescan."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import hmac
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from behique import __version__, api
from behique.config import Settings
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


_INLINE_SCRIPT = re.compile(rb"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script\s*>", re.S | re.I)


def _script_hashes(web_dir: Path) -> list[str]:
    """CSP hashes for the inline bootstrap scripts Next.js writes into exported pages."""
    hashes = set()
    for page in web_dir.rglob("*.html"):
        for body in _INLINE_SCRIPT.findall(page.read_bytes()):
            if body.strip():
                digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
                hashes.add(f"'sha256-{digest}'")
    return sorted(hashes)


def content_security_policy(script_hashes: list[str]) -> str:
    # Inline style attributes come from React and the resizable panels, so styles allow
    # 'unsafe-inline'; scripts stay limited to our own files and the hashed bootstraps.
    return "; ".join(
        [
            "default-src 'self'",
            "script-src " + " ".join(["'self'", *script_hashes]),
            "style-src 'self' 'unsafe-inline'",
            "connect-src 'self'",
            "img-src 'self' data:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
    )


class _SecurityHeaders:
    def __init__(self, app, csp: str) -> None:
        self.app, self.csp = app, csp.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"content-security-policy", self.csp),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


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
    settings = service.settings if service else Settings()
    web_dir = settings.web_dir
    has_web = (web_dir / "index.html").is_file()
    if has_web:  # registered last so /api and /mcp win
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    app.add_middleware(_McpSlash)
    if settings.dev_cors:  # `pnpm dev` on :3000 talking to this server
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(
        _SecurityHeaders,
        csp=content_security_policy(_script_hashes(web_dir) if has_web else []),
    )
    return app


def app() -> FastAPI:  # uvicorn --factory behique.main:app
    logging.basicConfig(level=logging.INFO)
    return create_app()
