from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.deps import budget
from app.rag import store
from app.ratelimit import limiter
from app.routes import chat, documents

log = logging.getLogger("kb")

SWEEP_INTERVAL_SECONDS = 900


async def _ttl_sweeper() -> None:
    """Delete expired chunks. This is what keeps demo storage bounded — without
    it, a public upload form fills the disk and never releases it."""
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            removed = await asyncio.to_thread(store.sweep_expired)
            if removed:
                log.info("ttl sweeper removed %d expired chunks", removed)
        except Exception:  # noqa: BLE001 - a failed sweep must not kill the app
            log.exception("ttl sweep failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.ensure_collection()

    async def _warm() -> None:
        """Load models off the request path so the first upload doesn't pay the
        download cost while a user watches a progress bar."""
        from app.rag import embed, retrieve

        try:
            await asyncio.to_thread(embed.warm)
            await asyncio.to_thread(retrieve.warm)
            log.info("models warm")
        except Exception:  # noqa: BLE001
            log.exception("model warmup failed; first request will be slow")

    warm_task = asyncio.create_task(_warm())
    sweep_task = asyncio.create_task(_ttl_sweeper())
    try:
        yield
    finally:
        for task in (warm_task, sweep_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Internal Knowledge Assistant", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # required: the session cookie carries the workspace
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Terlalu banyak permintaan dari alamat ini. "
                "Tunggu sebentar lalu coba lagi."
            )
        },
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "demo_enabled": settings.demo_enabled,
        "llm_provider": settings.llm_provider,
        "llm_fallback": settings.llm_fallback_provider,
        "budget": budget.snapshot(),
    }


app.include_router(documents.router)
app.include_router(chat.router)
