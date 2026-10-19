"""Provider-agnostic streaming chat, with automatic failover.

Gemini is primary; Groq takes over on 429/rate-limit or 5xx. This matters most
at exactly the moment it is hardest to fix: the minutes after a demo link is
shared, when concurrent visitors are most likely to trip a per-minute quota.

Failover only triggers on *transient* provider failures. A malformed request or
a bad API key must surface, not be silently retried against a second provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol


class TransientProviderError(Exception):
    """Rate-limited or server-side failure: worth retrying elsewhere."""


class ProviderUnavailable(Exception):
    """Provider is not configured (no API key)."""


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


class ChatProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def stream_chat(
        self, system: str, messages: list[Message]
    ) -> AsyncIterator[str]: ...


@dataclass
class StreamOutcome:
    """Which provider actually answered — surfaced to tracing and the client."""

    provider: str = ""
    failed_over_from: str | None = None
    errors: list[str] = field(default_factory=list)


async def stream_with_fallback(
    providers: list[ChatProvider],
    system: str,
    messages: list[Message],
    outcome: StreamOutcome,
) -> AsyncIterator[str]:
    """Yield text from the first provider that produces output.

    Once a provider has emitted its first token we are committed to it — a
    mid-stream failure cannot be retried without showing the user a half
    answer followed by a different one.
    """
    usable = [p for p in providers if p.available()]
    if not usable:
        raise ProviderUnavailable(
            "Tidak ada penyedia LLM yang terkonfigurasi. Set GEMINI_API_KEY, "
            "GROQ_API_KEY, atau OPENAI_API_KEY."
        )

    for index, provider in enumerate(usable):
        started = False
        try:
            async for piece in provider.stream_chat(system, messages):
                if not started:
                    started = True
                    outcome.provider = provider.name
                    if index > 0:
                        outcome.failed_over_from = usable[index - 1].name
                yield piece
            return
        except TransientProviderError as exc:
            outcome.errors.append(f"{provider.name}: {exc}")
            if started:
                raise
            continue  # try the next provider

    raise TransientProviderError(
        "Semua penyedia LLM sedang kena batas kuota. Coba lagi beberapa saat lagi. "
        f"({'; '.join(outcome.errors)})"
    )


def build_chain() -> list[ChatProvider]:
    """Assemble the provider chain from settings, primary first."""
    from app.config import settings
    from app.llm.anthropic_provider import AnthropicProvider
    from app.llm.gemini import GeminiProvider
    from app.llm.groq_provider import GroqProvider
    from app.llm.openai_provider import OpenAIProvider

    registry = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    names = [settings.llm_provider]
    if settings.llm_fallback_provider not in ("none", settings.llm_provider):
        names.append(settings.llm_fallback_provider)
    return [registry[n]() for n in names if n in registry]
