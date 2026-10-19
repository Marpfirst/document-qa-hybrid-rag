"""PDF extraction with per-page routing.

Heading detection in PDF is a heuristic: there is no heading markup, only font
size and weight. Lines noticeably larger than the page's body text, or bold and
short, are promoted to Markdown headings so chunk.py can see them. This will
miss on unusual layouts — an acknowledged limitation, and the reason DOCX
(which carries real heading styles) is the cleaner path.
"""

from __future__ import annotations

import fitz  # pymupdf

from app.config import settings
from app.ingest import chunk as chunker
from app.ingest.router import classify, signals_from_text
from app.schemas import ParsedDocument


class ParseError(Exception):
    """Raised with a user-facing message."""


def _page_image_coverage(page: fitz.Page) -> float:
    """Fraction of the page covered by its largest image."""
    page_area = abs(page.rect.width * page.rect.height) or 1.0
    largest = 0.0
    try:
        for info in page.get_image_info():
            bbox = info.get("bbox")
            if not bbox:
                continue
            w = abs(bbox[2] - bbox[0])
            h = abs(bbox[3] - bbox[1])
            largest = max(largest, w * h)
    except Exception:
        return 0.0
    return min(largest / page_area, 1.0)


def _markup_headings(page: fitz.Page) -> str:
    """Rebuild the page as text, prefixing likely headings with Markdown hashes."""
    try:
        data = page.get_text("dict")
    except Exception:
        return page.get_text("text")

    lines: list[tuple[str, float, bool]] = []
    sizes: list[float] = []
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            size = max(float(s.get("size", 0)) for s in spans)
            bold = any("bold" in str(s.get("font", "")).lower() for s in spans)
            lines.append((text, size, bold))
            sizes.extend([size] * len(text))

    if not lines:
        return page.get_text("text")

    sizes.sort()
    body_size = sizes[len(sizes) // 2]  # char-weighted median = body text size

    out: list[str] = []
    for text, size, bold in lines:
        already_marked = chunker.heading_level(text) is not None
        if already_marked:
            out.append(text)
            continue
        is_big = size >= body_size * 1.15
        is_short = len(text) <= 90
        if is_short and (is_big or (bold and size >= body_size)):
            level = 1 if size >= body_size * 1.4 else 2
            out.append("#" * level + " " + text)
        else:
            out.append(text)
    return "\n".join(out)


def parse_pdf(data: bytes) -> ParsedDocument:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise ParseError("PDF tidak bisa dibuka atau rusak.")

    with doc:
        if doc.needs_pass:
            raise ParseError(
                "PDF ini terenkripsi/berpassword. Buka proteksinya lalu unggah ulang."
            )
        if doc.page_count > settings.max_pages_per_doc:
            raise ParseError(
                f"PDF punya {doc.page_count} halaman, melebihi batas "
                f"{settings.max_pages_per_doc} halaman."
            )

        result = ParsedDocument(pages_total=doc.page_count)
        readable: list[tuple[int | None, str]] = []

        for index in range(doc.page_count):
            page = doc.load_page(index)
            raw = page.get_text("text")
            sig = signals_from_text(
                raw,
                has_fonts=bool(page.get_fonts()),
                image_coverage=_page_image_coverage(page),
            )
            verdict = classify(sig)

            if verdict == "digital":
                result.pages_digital += 1
                readable.append((index + 1, _markup_headings(page)))
            elif verdict == "scanned":
                result.pages_scanned += 1
                result.pages_ocr_pending += 1
            elif verdict == "broken_text_layer":
                result.pages_broken += 1
                result.pages_ocr_pending += 1
            else:
                result.pages_blank += 1

    result.chunks = chunker.chunk_pages(readable)
    return result
