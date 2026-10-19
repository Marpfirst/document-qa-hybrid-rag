"""Request-scoped dependencies: workspace resolution and the global LLM budget."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date

from fastapi import Cookie, Response

from app.config import settings
from app.security import (
    SESSION_COOKIE,
    new_workspace_id,
    sign_workspace,
    verify_workspace,
)


@dataclass
class WorkspaceSession:
    id: str
    cookie_value: str | None = None  # set only when a new session was minted

    def apply(self, response: Response) -> None:
        """Attach the session cookie, if one needs setting.

        Routes that return their own Response object must call this: FastAPI
        only merges the injected Response's headers when it builds the response
        itself, so a StreamingResponse would otherwise drop the cookie and the
        visitor would get a fresh, empty workspace on every request.
        """
        if not self.cookie_value:
            return
        response.set_cookie(
            SESSION_COOKIE,
            self.cookie_value,
            max_age=settings.workspace_ttl_hours * 3600,
            httponly=True,
            samesite="lax",
            secure=settings.cors_origins.startswith("https"),
        )


def workspace_session(
    response: Response,
    kb_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> WorkspaceSession:
    """Derive the caller's workspace from an HMAC-signed cookie, minting one on
    first visit. The request body is never consulted — see security.py."""
    workspace_id = verify_workspace(kb_session)
    if workspace_id is not None:
        return WorkspaceSession(id=workspace_id)

    workspace_id = new_workspace_id()
    session = WorkspaceSession(id=workspace_id, cookie_value=sign_workspace(workspace_id))
    session.apply(response)  # covers routes where FastAPI builds the response
    return session


class DailyBudget:
    """Process-wide cap on LLM calls, on top of the provider's own quota.

    Rate limits stop a burst; this stops a slow drip from exhausting the daily
    free-tier allowance before the day is out. Resets at UTC midnight.
    """

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._day = date.today()
        self._used = 0
        self._lock = threading.Lock()

    def _roll(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._used = 0

    def try_consume(self, n: int = 1) -> bool:
        with self._lock:
            self._roll()
            if self._used + n > self._limit:
                return False
            self._used += n
            return True

    def snapshot(self) -> dict:
        with self._lock:
            self._roll()
            return {"used": self._used, "limit": self._limit}


budget = DailyBudget(settings.daily_llm_call_budget)
