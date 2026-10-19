"""End-to-end parsing against real PDF/DOCX bytes.

The mixed-PDF case is the one that justifies routing per page instead of per
document, and the scanned case is the one that must fail *loudly* in release 1
rather than silently indexing nothing.
"""

import pytest

from app.ingest.parse_docx import parse_docx
from app.ingest.parse_pdf import ParseError, parse_pdf
from tests import fixtures


def test_digital_pdf_yields_chunks_with_heading_paths():
    result = parse_pdf(fixtures.digital_pdf())
    assert result.pages_digital == 1
    assert result.pages_scanned == 0
    assert result.chunks

    leave = next((c for c in result.chunks if "12 hari kerja" in c.text), None)
    assert leave is not None, "annual-leave section should be extracted"
    assert leave.page == 1
    assert leave.heading_path, "chunk must carry a heading path for citations"


def test_scanned_pdf_produces_no_chunks_but_reports_why():
    result = parse_pdf(fixtures.scanned_pdf())
    assert result.pages_scanned == 1
    assert result.chunks == []
    note = result.skipped_note()
    assert note and "scan" in note.lower()


def test_mixed_pdf_reads_body_and_flags_only_the_scanned_cover():
    """Per-document routing would either skip the whole file or OCR all of it."""
    result = parse_pdf(fixtures.mixed_pdf())
    assert result.pages_total == 2
    assert result.pages_scanned == 1
    assert result.pages_digital == 1
    assert result.chunks, "the digital body page must still be indexed"
    assert any("12 hari kerja" in c.text for c in result.chunks)


def test_broken_text_layer_is_not_indexed():
    """Text extracts fine but is garbage; indexing it would poison retrieval."""
    result = parse_pdf(fixtures.broken_text_layer_pdf())
    assert result.pages_broken == 1
    assert result.pages_digital == 0
    assert result.chunks == []


def test_encrypted_pdf_is_rejected_with_actionable_message():
    doc_bytes = fixtures.digital_pdf()
    import fitz

    doc = fitz.open(stream=doc_bytes, filetype="pdf")
    encrypted = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="x", user_pw="y")
    doc.close()

    with pytest.raises(ParseError) as exc:
        parse_pdf(encrypted)
    assert "password" in str(exc.value).lower() or "terenkripsi" in str(exc.value).lower()


def test_corrupt_pdf_is_rejected():
    with pytest.raises(ParseError):
        parse_pdf(b"%PDF-1.4 this is not actually a pdf")


def test_docx_heading_styles_give_exact_paths():
    """Word carries real heading styles, so paths are read rather than guessed."""
    result = parse_docx(fixtures.sop_docx())
    leave = next(c for c in result.chunks if "12 hari kerja" in c.text)
    assert leave.heading_path == ["SOP CUTI KARYAWAN", "4. Cuti", "4.2 Cuti Tahunan"]


def test_docx_table_rows_repeat_their_headers():
    """A retrieved table row has to say what its columns mean."""
    result = parse_docx(fixtures.sop_docx())
    joined = "\n".join(c.text for c in result.chunks)
    assert "Jenis Cuti: Cuti Besar" in joined
    assert "Penyetuju: Kepala Divisi" in joined


def test_docx_without_text_is_rejected():
    from docx import Document
    import io

    buffer = io.BytesIO()
    Document().save(buffer)
    with pytest.raises(ParseError):
        parse_docx(buffer.getvalue())
