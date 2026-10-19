"""Gemini provider — primary for both chat and (release 2) vision OCR."""

from __future__ import annotations

from typing import AsyncIterator

from app.config import settings
from app.llm.base import Message, TransientProviderError

_TRANSIENT_MARKERS = (
    "429",
    "rate limit",
    "resource_exhausted",
    "quota",
    "500",
    "502",
    "503",
    "504",
    "unavailable",
    "overloaded",
    "deadline",
)


def looks_transient(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


class GeminiProvider:
    name = "gemini"

    def available(self) -> bool:
        return bool(settings.gemini_api_key)

    async def stream_chat(
        self, system: str, messages: list[Message]
    ) -> AsyncIterator[str]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part.from_text(text=m.content)],
            )
            for m in messages
        ]
        try:
            stream = await client.aio.models.generate_content_stream(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                ),
            )
            async for event in stream:
                text = getattr(event, "text", None)
                if text:
                    yield text
        except Exception as exc:  # noqa: BLE001 - classified below
            if looks_transient(exc):
                raise TransientProviderError(str(exc)) from exc
            raise
