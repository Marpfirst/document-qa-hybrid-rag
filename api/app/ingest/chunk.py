"""Section-aware chunking.

The unit of retrieval is a *leaf section* — the smallest heading-delimited block
of text — not a fixed token window. Each chunk carries the heading path that
leads to it, which is prepended to the embedded text (see Chunk.embedding_text).

That prepending is the highest-leverage, cheapest recall win in SOP documents:
a section titled "4.2 Cuti Tahunan" whose body reads "Diberikan 12 hari kerja
per tahun" contains no searchable mention of leave at all on its own.
"""

from __future__ import annotations

import re

from app.config import settings
from app.schemas import Chunk

# ~4 chars per token is a rough but stable heuristic for Indonesian and English.
CHARS_PER_TOKEN = 4

# "BAB III KETENTUAN UMUM", "Pasal 12" — legal markers stand alone as headings,
# so the trailing title is optional here.
LEGAL_HEADING = re.compile(
    r"^\s*(?:BAB|BAGIAN|PASAL)\s+[IVXLC\d]+[.:]?(?:\s+\S.{0,110})?$",
    re.IGNORECASE,
)

# "4.2 Cuti Tahunan", "A. Ruang Lingkup" — a bare number is not a heading
# (it would match page numbers), so a title is required for these.
NUMBERED_HEADING = re.compile(
    r"^\s*(?P<marker>\d+(?:\.\d+)*\.?|[A-Z]\.)\s+(?P<title>\S.{0,110})$"
)


def heading_level(line: str) -> int | None:
    """Return a nesting depth for a heading line, or None if it isn't one."""
    text = line.strip()
    if not text or len(text) > 120:
        return None

    if text.startswith("#"):
        hashes = len(text) - len(text.lstrip("#"))
        if 1 <= hashes <= 6 and text[hashes : hashes + 1] in (" ", ""):
            return hashes

    if LEGAL_HEADING.match(text):
        return 1

    m = NUMBERED_HEADING.match(text)
    if m:
        marker = m.group("marker").strip().rstrip(".")
        if marker[0].isalpha():
            return 2
        return min(marker.count(".") + 1, 6)

    # ALL-CAPS standalone line, no sentence punctuation: a title in practice.
    if text.isupper() and len(text.split()) <= 12 and not text.endswith((".", ":")):
        return 1
    return None


def _strip_marker(line: str) -> str:
    text = line.strip()
    if text.startswith("#"):
        return text.lstrip("#").strip()
    return text


def _split_oversized(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    """Split a too-long section on paragraph boundaries, with overlap."""
    if len(text) <= target_chars:
        return [text]

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    slices: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > target_chars:
            slices.append(current.strip())
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = (tail + "\n\n" + para) if tail else para
        else:
            current = (current + "\n\n" + para) if current else para
    if current.strip():
        slices.append(current.strip())

    # A single paragraph longer than the target still needs breaking up.
    final: list[str] = []
    for s in slices:
        while len(s) > target_chars * 1.5:
            cut = s.rfind(" ", 0, target_chars)
            cut = cut if cut > target_chars // 2 else target_chars
            final.append(s[:cut].strip())
            s = s[max(0, cut - overlap_chars) :].strip()
        if s:
            final.append(s)
    return final


def chunk_pages(
    pages: list[tuple[int | None, str]], *, is_ocr: bool = False
) -> list[Chunk]:
    """Turn (page_number, text) pairs into section-aware chunks.

    Page numbers are carried through so citations can name a page even when the
    section spans several. `char_start`/`char_end` are offsets into the
    concatenated document text, used for precise highlighting.
    """
    target_chars = settings.chunk_target_tokens * CHARS_PER_TOKEN
    overlap_chars = settings.chunk_overlap_tokens * CHARS_PER_TOKEN

    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    buffer_page: int | None = None
    buffer_start = 0
    cursor = 0

    def flush(end_offset: int) -> None:
        nonlocal buffer, buffer_page, buffer_start
        body = "\n".join(buffer).strip()
        buffer = []
        if not body:
            return
        path = [title for _, title in heading_stack]
        for piece in _split_oversized(body, target_chars, overlap_chars):
            chunks.append(
                Chunk(
                    text=piece,
                    heading_path=list(path),
                    page=buffer_page,
                    char_start=buffer_start,
                    char_end=end_offset,
                    is_ocr=is_ocr,
                )
            )
        buffer_page = None

    for page_no, page_text in pages:
        for line in page_text.splitlines():
            line_len = len(line) + 1
            level = heading_level(line)
            if level is not None:
                flush(cursor)
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, _strip_marker(line)))
                buffer_start = cursor + line_len
                buffer_page = page_no
            elif line.strip():
                if not buffer:
                    buffer_start = cursor
                    buffer_page = page_no
                buffer.append(line)
            elif buffer:
                buffer.append("")
            cursor += line_len

    flush(cursor)

    # A document with no detectable headings still has to produce chunks.
    if not chunks:
        joined = "\n".join(text for _, text in pages).strip()
        if joined:
            first_page = pages[0][0] if pages else None
            offset = 0
            for piece in _split_oversized(joined, target_chars, overlap_chars):
                chunks.append(
                    Chunk(
                        text=piece,
                        heading_path=[],
                        page=first_page,
                        char_start=offset,
                        char_end=offset + len(piece),
                        is_ocr=is_ocr,
                    )
                )
                offset += len(piece)
    return chunks
