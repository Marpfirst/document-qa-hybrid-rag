"""The evaluation is only worth reporting if its own scoring is right."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval import corpus
from eval.metrics import (
    abstained,
    answer_correct,
    gold_rank,
    is_gold,
    latency_summary,
    normalize,
    retrieval_summary,
    section_key,
)

GOLD = {"doc": "a.docx", "sections": ["4.2", "6"]}


def test_section_key_reads_the_leading_number():
    assert section_key(["SOP CUTI", "4. Cuti", "4.2 Cuti Tahunan"]) == "4.2"
    assert section_key(["SOP CUTI", "5. Prosedur Pengajuan"]) == "5"
    assert section_key(["SOP CUTI DAN KEHADIRAN KARYAWAN"]) == "intro"


def test_is_gold_needs_same_document_and_section():
    assert is_gold("a.docx", ["X", "4.2 Cuti Tahunan"], GOLD)
    assert not is_gold("b.docx", ["X", "4.2 Cuti Tahunan"], GOLD)
    assert not is_gold("a.docx", ["X", "4.3 Cuti Besar"], GOLD)
    assert not is_gold("a.docx", ["X", "4.2 Cuti Tahunan"], None)


def test_gold_rank_is_one_based_and_none_when_missing():
    ranked = [("a.docx", ["X", "3.1 Jam"]), ("a.docx", ["X", "6. Matriks"]), ("a.docx", ["X", "4.2 Cuti"])]
    assert gold_rank(ranked, GOLD) == 2
    assert gold_rank(ranked[:1], GOLD) is None


def test_retrieval_summary_counts_hits_and_mrr():
    summary = retrieval_summary([1, 3, None, 2])
    assert summary["n"] == 4
    assert summary["hit@1"] == 0.25
    assert summary["hit@3"] == 0.75
    assert summary["hit@8"] == 0.75
    assert summary["mrr"] == round((1 + 1 / 3 + 0 + 1 / 2) / 4, 3)


@pytest.mark.parametrize(
    "text",
    [
        "Informasi itu tidak ada di dokumen yang diunggah.",
        "Dokumen tidak memuat kebijakan tersebut.",
        "Kebijakan WFH tidak diatur dalam dokumen ini.",
        "This is not mentioned in the uploaded documents.",
        "The document does not specify a dress code.",
    ],
)
def test_abstention_is_detected(text):
    assert abstained(text)


def test_a_real_answer_is_not_an_abstention():
    assert not abstained("Cuti tahunan diberikan sebanyak 12 hari kerja per tahun [doc:2].")


def test_answer_correct_requires_all_patterns_and_no_forbidden_one():
    answer = "Pengajuan paling lambat 7 hari kerja sebelum tanggal cuti [doc:1]."
    assert answer_correct(answer, ["7 hari kerja"])
    assert not answer_correct(answer, ["7 hari kerja", "Kepala Divisi"])
    assert not answer_correct(answer, ["7 hari kerja"], forbid=["sebelum tanggal"])
    assert answer_correct("Batas hotel Rp1.200.000 per malam", [r"1\.200\.000"])


def test_latency_summary():
    assert latency_summary([]) == {"median_s": None, "p90_s": None}
    assert latency_summary([1.0, 2.0, 3.0])["median_s"] == 2.0


def test_questions_file_is_well_formed():
    questions = json.loads((Path(corpus.__file__).parent / "questions.json").read_text(encoding="utf-8"))
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))
    files = set(corpus.documents())
    for q in questions:
        if q.get("expect_abstain"):
            assert q["gold"] is None
        else:
            assert q["gold"]["doc"] in files
            assert q["gold"]["sections"]
            assert q["must"]


def test_every_gold_section_exists_in_the_corpus():
    """A typo in a gold section would silently turn a hit into a miss."""
    from app.ingest.parse_docx import parse_docx

    found: dict[str, set[str]] = {}
    for name, data in corpus.documents().items():
        found[name] = {section_key(c.heading_path) for c in parse_docx(data).chunks}
    questions = json.loads((Path(corpus.__file__).parent / "questions.json").read_text(encoding="utf-8"))
    for q in questions:
        gold = q["gold"]
        if gold:
            for section in gold["sections"]:
                assert section in found[gold["doc"]], (q["id"], section)


def test_normalize_handles_no_break_spaces_and_hyphens():
    answer = "Kata sandi diganti setiap" + chr(0x202F) + "90" + chr(0x202F) + "hari (SOP" + chr(0x2011) + "IT" + chr(0x2011) + "007)."
    assert normalize(answer) == "Kata sandi diganti setiap 90 hari (SOP-IT-007)."
    assert answer_correct(answer, ["90 hari", "SOP-IT-007"])


def test_abstention_covers_terdapat_and_dollar_spacing():
    assert abstained("Informasi tersebut tidak terdapat dalam dokumen yang Anda unggah.")
    assert answer_correct("Uang makan adalah US $50 per hari.", [r"US\s*\$\s*50|50\s*(dolar|USD)"])
