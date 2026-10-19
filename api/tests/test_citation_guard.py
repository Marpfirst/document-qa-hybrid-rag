"""The citation guard is the substitute for provider-native citations.

Its job is to assume the model is unreliable and check every `[doc:N]` against
the contexts that were actually sent.
"""

import pytest

from app.rag.citation_guard import validate
from app.schemas import RetrievedChunk


def ctx(ref: int, text: str = "Cuti tahunan 12 hari kerja.") -> RetrievedChunk:
    return RetrievedChunk(
        ref=ref,
        doc_name="SOP Cuti.pdf",
        heading_path=["4. Cuti", "4.2 Cuti Tahunan"],
        page=3,
        text=text,
    )


def test_valid_citation_is_kept_and_resolved_to_metadata():
    result = validate("Cuti tahunan 12 hari kerja [doc:1].", [ctx(1)])
    assert "[doc:1]" in result.text
    assert result.accepted == 1
    assert result.rejected == 0
    assert result.citations[0].doc_name == "SOP Cuti.pdf"
    assert result.citations[0].page == 3


def test_fabricated_citation_is_stripped_before_reaching_the_user():
    """The headline case: the model cites a context that was never sent."""
    result = validate("Cuti tahunan 12 hari kerja [doc:99].", [ctx(1)])
    assert "[doc:99]" not in result.text
    assert "99" not in result.text
    assert result.rejected == 1
    assert result.citations == []


def test_mixed_citation_keeps_the_real_ref_and_drops_the_fake():
    result = validate("Disetujui atasan [doc:1,99].", [ctx(1)])
    assert "[doc:1]" in result.text
    assert "99" not in result.text
    assert result.accepted == 1
    assert result.rejected == 1


def test_precision_is_reportable():
    result = validate("A [doc:1] B [doc:2] C [doc:98] D [doc:99]", [ctx(1), ctx(2)])
    assert result.accepted == 2
    assert result.rejected == 2
    assert result.precision == 0.5


def test_no_citations_means_no_precision_signal():
    result = validate("Saya tidak menemukan informasi itu di dokumen.", [ctx(1)])
    assert result.precision is None
    assert result.citations == []


def test_duplicate_refs_produce_one_citation_entry():
    result = validate("A [doc:1] dan B [doc:1].", [ctx(1)])
    assert len(result.citations) == 1
    assert result.accepted == 2


def test_whitespace_left_by_a_stripped_tag_is_cleaned_up():
    result = validate("Cuti 12 hari [doc:99] .", [ctx(1)])
    assert "  " not in result.text
    assert result.text.endswith(".")


def test_spacing_variants_are_matched():
    result = validate("A [DOC: 1] B [doc:2 ]", [ctx(1), ctx(2)])
    assert result.accepted == 2
    assert result.rejected == 0


def test_repeated_doc_prefix_inside_one_bracket_is_matched():
    """Observed from a live Gemini response: "[doc:1, doc:2]".

    An unmatched form leaks the raw marker into the answer text *and* silently
    drops a real citation, so every multi-ref spelling has to be handled.
    """
    result = validate("Disetujui Kepala Divisi [doc:1, doc:2].", [ctx(1), ctx(2)])
    assert result.accepted == 2
    assert len(result.citations) == 2
    assert "doc:1" not in result.text.replace("[doc:1]", "").replace("[doc:2]", "")


@pytest.mark.parametrize(
    "marker",
    ["[doc:1,2]", "[doc:1, doc:2]", "[doc:1; doc:2]", "[doc: 1 , doc: 2 ]", "[doc:1][doc:2]"],
)
def test_all_multi_ref_spellings_resolve_to_both_refs(marker):
    result = validate(f"Klaim {marker}.", [ctx(1), ctx(2)])
    assert result.accepted == 2, f"{marker} not fully parsed"
    assert {c.ref for c in result.citations} == {1, 2}


def test_long_context_quote_is_truncated_for_the_popover():
    long_text = "Ketentuan cuti. " * 200
    result = validate("Lihat [doc:1].", [ctx(1, long_text)])
    assert len(result.citations[0].quote) <= 401
    assert result.citations[0].quote.endswith("…")
