"""Chunking must produce leaf sections that carry their heading path.

The heading path is not decoration: it is prepended to the embedded text, and
it is what makes a short section like "Diberikan 12 hari kerja" findable by a
query about annual leave.
"""

from app.ingest.chunk import chunk_pages, heading_level

DOC = """# SOP CUTI KARYAWAN

## 4. Cuti

### 4.2 Cuti Tahunan

Diberikan sebanyak 12 hari kerja per tahun.

### 4.3 Persetujuan

Pengajuan disetujui oleh atasan langsung.
"""


def test_heading_level_recognizes_markdown():
    assert heading_level("# BAB I") == 1
    assert heading_level("### 4.2 Cuti Tahunan") == 3


def test_heading_level_recognizes_numbered_and_legal_markers():
    assert heading_level("4.2 Cuti Tahunan") == 2
    assert heading_level("4.2.1 Pengajuan") == 3
    assert heading_level("BAB III KETENTUAN UMUM") == 1
    assert heading_level("Pasal 12") == 1
    assert heading_level("A. Ruang Lingkup") == 2


def test_heading_level_rejects_prose():
    assert heading_level("Diberikan sebanyak 12 hari kerja per tahun.") is None
    assert heading_level("") is None


def test_leaf_sections_become_chunks_with_full_heading_path():
    chunks = chunk_pages([(1, DOC)])
    by_text = {c.text: c for c in chunks}

    leave = next(c for t, c in by_text.items() if "12 hari kerja" in t)
    assert leave.heading_path == ["SOP CUTI KARYAWAN", "4. Cuti", "4.2 Cuti Tahunan"]

    approval = next(c for t, c in by_text.items() if "atasan langsung" in t)
    assert approval.heading_path == ["SOP CUTI KARYAWAN", "4. Cuti", "4.3 Persetujuan"]


def test_embedding_text_prepends_heading_path():
    chunks = chunk_pages([(1, DOC)])
    leave = next(c for c in chunks if "12 hari kerja" in c.text)
    embedded = leave.embedding_text()
    assert embedded.startswith("SOP CUTI KARYAWAN > 4. Cuti > 4.2 Cuti Tahunan")
    assert "12 hari kerja" in embedded


def test_sibling_heading_pops_stack_rather_than_nesting():
    chunks = chunk_pages([(1, DOC)])
    paths = [c.heading_path for c in chunks]
    # 4.3 must not end up nested underneath 4.2
    assert not any("4.2 Cuti Tahunan" in p and "4.3 Persetujuan" in p for p in paths)


def test_page_number_is_carried_for_citations():
    chunks = chunk_pages([(7, DOC)])
    assert all(c.page == 7 for c in chunks)


def test_document_without_headings_still_produces_chunks():
    plain = "Karyawan berhak atas cuti. " * 20
    chunks = chunk_pages([(1, plain)])
    assert chunks
    assert chunks[0].heading_path == []


def test_oversized_section_is_split_with_overlap():
    long_body = "\n\n".join(f"Paragraf nomor {i} berisi ketentuan teknis." * 20 for i in range(40))
    chunks = chunk_pages([(1, "# Bagian Panjang\n\n" + long_body)])
    assert len(chunks) > 1
    assert all(c.heading_path == ["Bagian Panjang"] for c in chunks)


def test_char_offsets_are_monotonic():
    chunks = chunk_pages([(1, DOC)])
    for c in chunks:
        assert c.char_end >= c.char_start
