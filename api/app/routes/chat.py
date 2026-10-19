"""Streaming chat endpoint.

The `retrieval` event is emitted *before* the first text delta so the trace
panel fills immediately — the demo feels responsive, and the retrieved context
is visible even while the answer is still being written.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.deps import WorkspaceSession, budget, workspace_session
from app.llm.base import (
    Message,
    ProviderUnavailable,
    StreamOutcome,
    TransientProviderError,
)
from app.rag import citation_guard, generate, retrieve
from app.ratelimit import limiter
from app.schemas import ChatRequest

router = APIRouter(tags=["chat"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(payload: ChatRequest, workspace_id: str) -> AsyncIterator[str]:
    history = [Message(role=t.role, content=t.content) for t in payload.history]
    search_query = generate.condense_question(payload.message, history)

    try:
        chunks = retrieve.retrieve(workspace_id, search_query)
    except Exception as exc:  # noqa: BLE001 - reported to the client as an error event
        yield sse("error", {"message": f"Pencarian gagal: {exc}"})
        yield sse("done", {})
        return

    yield sse(
        "retrieval",
        {
            "query": search_query,
            "chunks": [c.model_dump() for c in chunks],
        },
    )

    if not chunks:
        yield sse("delta", {"text": generate.NO_CONTEXT_REPLY[payload.lang]})
        yield sse("done", {"citations": [], "grounded": False})
        return

    if not budget.try_consume():
        yield sse(
            "error",
            {
                "message": (
                    "Kuota harian demo sudah habis. Silakan coba lagi besok — "
                    "atau jalankan sendiri secara lokal dengan API key kamu."
                )
            },
        )
        yield sse("done", {})
        return

    outcome = StreamOutcome()
    parts: list[str] = []
    try:
        async for piece in generate.stream_answer(
            payload.message, chunks, history, outcome, payload.lang
        ):
            parts.append(piece)
            yield sse("delta", {"text": piece})
    except ProviderUnavailable as exc:
        yield sse("error", {"message": str(exc)})
        yield sse("done", {})
        return
    except TransientProviderError as exc:
        yield sse("error", {"message": str(exc)})
        yield sse("done", {})
        return
    except Exception as exc:  # noqa: BLE001
        yield sse("error", {"message": f"Gagal menghasilkan jawaban: {exc}"})
        yield sse("done", {})
        return

    guard = citation_guard.validate("".join(parts), chunks)
    yield sse(
        "citation",
        {
            "citations": [c.model_dump() for c in guard.citations],
            "accepted": guard.accepted,
            "rejected": guard.rejected,
            "precision": guard.precision,
        },
    )
    yield sse(
        "done",
        {
            "provider": outcome.provider,
            "failed_over_from": outcome.failed_over_from,
            "clean_text": guard.text,
            "citations_rejected": guard.rejected,
        },
    )


@router.post("/chat/stream")
@limiter.limit(settings.rate_limit_chat)
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    session: WorkspaceSession = Depends(workspace_session),
) -> StreamingResponse:
    if not settings.demo_enabled:
        raise HTTPException(503, "Demo sedang dinonaktifkan sementara.")

    response = StreamingResponse(
        _event_stream(payload, session.id), media_type="text/event-stream"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    # FastAPI only merges the injected Response's headers when it builds the
    # response itself, so the session cookie must be applied here by hand.
    session.apply(response)
    return response
