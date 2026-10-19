"""Anthropic provider — inactive in the public demo, kept working on purpose.

Claude has no free tier, so the zero-cost demo runs on Gemini. This adapter
exists so `LLM_PROVIDER=anthropic` is a one-line switch rather than a rewrite,
and so the project can demonstrate the native `citations` path (server-provided
character offsets, which a model cannot fabricate) when a key is available.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import Message, TransientProviderError
from app.llm.gemini import looks_transient


class AnthropicProvider:
    name = "anthropic"

    def available(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def stream_chat(
        self, system: str, messages: list[Message]
    ) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        try:
            async with client.messages.stream(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                thinking={"type": "adaptive"},
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:  # noqa: BLE001 - classified below
            if looks_transient(exc):
                raise TransientProviderError(str(exc)) from exc
            raise
