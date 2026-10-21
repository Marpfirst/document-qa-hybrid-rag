"""Scoring helpers. Pure functions, no model calls, so they can be unit tested.

Answer scoring is deliberately plain string matching. An LLM judge would add a
second model whose own mistakes I would then have to measure. The cost is that a
correct answer worded differently from my pattern counts as wrong, so the runner
keeps every answer in the results file and the misses are read by hand.
"""

from __future__ import annotations

import re
from statistics import median

ABSTAIN_PATTERN = re.compile(
    r"tidak\s+(?:ada|terdapat|tertera|memuat|memiliki|ditemukan|disebutkan|disebut|diatur|dibahas|tercantum|termuat|menyebutkan|mengatur|membahas|menjelaskan|tersedia)"
    r"|belum\s+(?:ada|diatur)"
    r"|tidak\s+dapat\s+(?:menemukan|menjawab)"
    r"|(?:is|are)\s+not\s+(?:mentioned|specified|covered|included|stated|addressed|found|available)"
    r"|(?:does|do)\s+not\s+(?:mention|contain|specify|include|cover|address|provide|state)"
    r"|no\s+(?:information|mention|details)"
    r"|cannot\s+(?:find|answer)|can(?:'|’)t\s+(?:find|answer)",
    re.IGNORECASE,
)


def section_key(heading_path: list[str]) -> str:
    """Leading section number of the last heading ("4.2 Cuti Tahunan" -> "4.2")."""
    if len(heading_path) <= 1:
        return "intro"
    first = heading_path[-1].split()[0] if heading_path[-1].split() else ""
    return first.rstrip(".")


def is_gold(doc_name: str, heading_path: list[str], gold: dict | None) -> bool:
    if not gold:
        return False
    return doc_name == gold["doc"] and section_key(heading_path) in gold["sections"]


def gold_rank(ranked: list[tuple[str, list[str]]], gold: dict | None) -> int | None:
    """1-based rank of the first gold chunk, or None if it is not in the list."""
    for position, (doc_name, heading_path) in enumerate(ranked, start=1):
        if is_gold(doc_name, heading_path, gold):
            return position
    return None


def retrieval_summary(ranks: list[int | None], cutoffs: tuple[int, ...] = (1, 3, 8)) -> dict:
    n = len(ranks)
    out: dict = {"n": n}
    for k in cutoffs:
        out[f"hit@{k}"] = round(sum(1 for r in ranks if r is not None and r <= k) / n, 3) if n else None
    out["mrr"] = round(sum(1 / r for r in ranks if r) / n, 3) if n else None
    return out


_SPACES = re.compile("[" + "".join(map(chr, (0x00A0, 0x2007, 0x2009, 0x202F))) + "]")  # no-break, thin
_DASHES = re.compile("[" + chr(0x2010) + "-" + chr(0x2015) + chr(0x2212) + "]")  # hyphens, dashes, minus
_INVISIBLE = re.compile("[" + chr(0x200B) + "-" + chr(0x200D) + chr(0xFEFF) + "]")  # zero-width


def normalize(text: str) -> str:
    """Some models write no-break spaces and non-breaking hyphens in numbers and
    codes ("90<U+202F>hari"). They look identical on screen and would silently fail
    a plain match, so they are folded to ordinary spaces and hyphens first."""
    text = _INVISIBLE.sub("", _DASHES.sub("-", _SPACES.sub(" ", text)))
    return re.sub(r"\s+", " ", text)


def abstained(answer: str) -> bool:
    return bool(ABSTAIN_PATTERN.search(normalize(answer)))


def answer_correct(answer: str, must: list[str], forbid: list[str] | None = None) -> bool:
    text = normalize(answer)
    if not all(re.search(pattern, text, re.IGNORECASE) for pattern in must):
        return False
    return not any(re.search(pattern, text, re.IGNORECASE) for pattern in (forbid or []))


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return round(ordered[index], 2)


def latency_summary(values: list[float]) -> dict:
    return {
        "median_s": round(median(values), 2) if values else None,
        "p90_s": percentile(values, 0.9),
    }
