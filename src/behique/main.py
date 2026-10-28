"""App factory: REST routes, periodic rescan, and (later) MCP at /mcp."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from behique import __version__, api
from behique.service import Service, build_service

log = logging.getLogger(__name__)


async def _rescan_loop(svc: Service) -> None:
    while True:
        await asyncio.sleep(svc.settings.rescan_seconds)
        if not svc.rescan():
            log.info("rescan skipped: index run in progress")


def create_app(service: Service | None = None, *, rescan: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc = app.state.service = service or build_service()
        task = None
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
    return app


def app() -> FastAPI:  # uvicorn --factory behique.main:app
    logging.basicConfig(level=logging.INFO)
    return create_app()
