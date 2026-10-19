"""The page router decides what gets read, skipped, or sent to OCR.

Two of these cases are the ones a naive "does it have text?" check gets wrong,
and they are the reason this module exists.
"""

from app.ingest.router import classify, signals_from_text

BODY = (
    "Cuti tahunan diberikan sebanyak 12 hari kerja per tahun bagi karyawan "
    "yang telah bekerja sekurang-kurangnya 12 bulan secara terus menerus. "
    "Pengajuan diajukan paling lambat 7 hari sebelum tanggal cuti."
)


def test_digital_page_is_read_directly():
    sig = signals_from_text(BODY, has_fonts=True, image_coverage=0.0)
    assert classify(sig) == "digital"


def test_full_page_image_without_fonts_is_scanned():
    sig = signals_from_text("", has_fonts=False, image_coverage=0.95)
    assert classify(sig) == "scanned"


def test_near_empty_page_without_image_is_blank_not_scanned():
    """Cover pages and chapter dividers are legitimately near-empty.

    Routing these to OCR is the single biggest source of wasted quota.
    """
    sig = signals_from_text("BAB III", has_fonts=True, image_coverage=0.0)
    assert classify(sig) == "blank"


def test_broken_text_layer_detected_by_missing_word_breaks():
    """A broken CID map extracts plausible-length output with no spaces.

    Checking only for presence of text would wave this through and poison the
    index with unsearchable junk.
    """
    garbled = "".join("abcdefghij" for _ in range(30))
    sig = signals_from_text(garbled, has_fonts=True, image_coverage=0.0)
    assert classify(sig) == "broken_text_layer"


def test_broken_text_layer_detected_by_replacement_chars():
    text = "Cuti " + ("�" * 260)
    sig = signals_from_text(text, has_fonts=True, image_coverage=0.0)
    assert classify(sig) == "broken_text_layer"


def test_scanned_wins_over_blank_when_image_covers_page():
    sig = signals_from_text("3", has_fonts=False, image_coverage=0.9)
    assert classify(sig) == "scanned"
