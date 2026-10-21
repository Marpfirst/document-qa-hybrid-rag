"""Server-side validation of the model's citations.

Without a provider that returns server-computed citation offsets, the model is
asked to tag each claim with `[doc:N]`. That tag is a claim about the context,
and claims get verified: every N is checked against the contexts that were
actually sent, and anything else is stripped before the user ever sees it.

The rejection count is a reportable number — evidence that hallucinated
citations are handled, rather than an assertion that they don't happen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import Citation, RetrievedChunk

# Models write multi-references several ways, and an unmatched form would leak
# raw into the answer while silently losing a real citation. Accepted:
#   [doc:3]  [doc: 3]  [doc:3,5]  [doc:3, doc:5]  [doc:3; doc:5]  [doc:3][doc:5]
CITATION_PATTERN = re.compile(
    r"\[\s*doc:\s*(?P<body>[0-9]+(?:\s*[,;]\s*(?:doc:\s*)?[0-9]+)*)\s*\]",
    re.IGNORECASE,
)
_REF_NUMBER = re.compile(r"[0-9]+")

# Some models (gpt-oss) write the tag in full-width (CJK) brackets, e.g. U+3010 doc:1 U+3011.
# Fold them to ASCII first so the tag is validated like any other.
_BRACKETS = str.maketrans(
    {0x3010: "[", 0x3011: "]", 0xFF3B: "[", 0xFF3D: "]", 0x3014: "[", 0x3015: "]"}
)

MAX_QUOTE_CHARS = 400


@dataclass
class GuardResult:
    text: str
    citations: list[Citation] = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0

    @property
    def precision(self) -> float | None:
        total = self.accepted + self.rejected
        return (self.accepted / total) if total else None


def _quote_for(chunk: RetrievedChunk) -> str:
    quote = chunk.text.strip()
    if len(quote) <= MAX_QUOTE_CHARS:
        return quote
    return quote[:MAX_QUOTE_CHARS].rsplit(" ", 1)[0] + "…"


def validate(answer: str, contexts: list[RetrievedChunk]) -> GuardResult:
    """Strip unsupported citations, and collect metadata for the supported ones."""
    by_ref = {c.ref: c for c in contexts}
    result = GuardResult(text="")
    seen: set[int] = set()

    def replace(match: re.Match[str]) -> str:
        refs = [int(n) for n in _REF_NUMBER.findall(match.group("body"))]
        kept: list[int] = []
        for ref in refs:
            chunk = by_ref.get(ref)
            if chunk is None:
                # Fabricated reference: the model cited a context that was
                # never sent. Drop it silently and count it.
                result.rejected += 1
                continue
            result.accepted += 1
            kept.append(ref)
            if ref not in seen:
                seen.add(ref)
                result.citations.append(
                    Citation(
                        ref=ref,
                        doc_name=chunk.doc_name,
                        heading_path=chunk.heading_path,
                        page=chunk.page,
                        quote=_quote_for(chunk),
                        is_ocr=chunk.is_ocr,
                    )
                )
        if not kept:
            return ""
        return "".join(f"[doc:{r}]" for r in kept)

    cleaned = CITATION_PATTERN.sub(replace, answer.translate(_BRACKETS))
    # Collapse whitespace left behind by removed tags, without touching newlines.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)
    result.text = cleaned.strip()
    result.citations.sort(key=lambda c: c.ref)
    return result
