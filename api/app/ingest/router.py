"""Per-page verdict for PDFs: can we read this page's text, or not?

Deciding this per page rather than per document matters because real SOPs are
mixed: a scanned cover sheet in front of digitally-typeset body pages.

The verdicts are deliberately four, not two. "Has text / has no text" would
send cover pages and chapter dividers to OCR for nothing (they are legitimately
near-empty), and would wave through PDFs whose text layer extracts as garbage
from a broken encoding — silently poisoning the index with unsearchable junk.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.schemas import PageKind

REPLACEMENT_CHAR = "�"


@dataclass(frozen=True)
class PageSignals:
    """Everything the verdict is based on, kept separate from PyMuPDF so the
    decision logic is testable without constructing real PDFs."""

    char_count: int
    space_ratio: float
    replacement_ratio: float
    has_fonts: bool
    image_coverage: float


def signals_from_text(
    text: str, *, has_fonts: bool, image_coverage: float
) -> PageSignals:
    stripped = text.strip()
    n = len(stripped)
    spaces = sum(1 for ch in stripped if ch.isspace())
    replacements = stripped.count(REPLACEMENT_CHAR)
    return PageSignals(
        char_count=n,
        space_ratio=(spaces / n) if n else 0.0,
        replacement_ratio=(replacements / n) if n else 0.0,
        has_fonts=has_fonts,
        image_coverage=image_coverage,
    )


def classify(sig: PageSignals) -> PageKind:
    if sig.char_count >= settings.router_min_chars:
        # Text extracted, but is it real text? A broken CID map or a bad
        # PDF conversion yields plausible-length output with no word breaks.
        if sig.replacement_ratio > 0.1:
            return "broken_text_layer"
        if sig.space_ratio < settings.router_min_space_ratio:
            return "broken_text_layer"
        return "digital"

    # Below the text threshold: is there an image worth OCRing, or is the page
    # simply empty (cover, signature page, chapter divider)?
    if not sig.has_fonts and sig.image_coverage >= settings.router_min_image_coverage:
        return "scanned"
    if sig.char_count == 0 and sig.image_coverage >= settings.router_min_image_coverage:
        return "scanned"
    return "blank"
