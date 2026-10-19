"""Groq provider — automatic fallback when Gemini is rate-limited.

Not primary: its instruction-following on the `[doc:N]` citation format is
looser than Gemini's, and it is the same stack most comparable public demos
already run. As a fallback neither matters — it is only reached when the
alternative is no answer at all, and its LPU inference speed is a bonus there.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import Message, TransientProviderError
from app.llm.gemini import looks_transient


class GroqProvider:
    name = "groq"

    def available(self) -> bool:
        return bool(settings.groq_api_key)

    async def stream_chat(
        self, system: str, messages: list[Message]
    ) -> AsyncIterator[str]:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)
        payload = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]
        try:
            stream = await client.chat.completions.create(
                model=settings.groq_model,
                messages=payload,
                max_tokens=2048,
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
