"""OpenAI provider — opt-in via `LLM_PROVIDER=openai`.

Unlike Gemini and Groq this one has no free tier: every call is billed, so the
daily call budget is the only thing standing between a shared demo link and an
invoice.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import Message, TransientProviderError
from app.llm.gemini import looks_transient


class OpenAIProvider:
    name = "openai"

    def available(self) -> bool:
        return bool(settings.openai_api_key)

    async def stream_chat(
        self, system: str, messages: list[Message]
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        payload = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]
        try:
            stream = await client.chat.completions.create(
                model=settings.openai_model,
                messages=payload,
                max_completion_tokens=2048,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content
                if piece:
                    yield piece
        except Exception as exc:  # noqa: BLE001 - classified below
            if looks_transient(exc):
                raise TransientProviderError(str(exc)) from exc
            raise
