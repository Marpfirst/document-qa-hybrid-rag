"""Upload validation and session signing.

Two invariants this module exists to protect:

1. `workspace_id` is derived from an HMAC-signed cookie, never from the request
   body. If a client could name its own workspace, anyone could enumerate IDs
   and read other people's documents.
2. Uploaded files are untrusted input. Filenames never reach the filesystem,
   declared content types are never believed, and compressed formats are
   checked for decompression-bomb ratios before being opened.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import secrets
import zipfile

from app.config import settings

SESSION_COOKIE = "kb_session"

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"
MAX_DECOMPRESSION_RATIO = 100
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


class UploadRejected(Exception):
    """Raised with a message meant to be shown to the user verbatim."""


# --- session signing ---------------------------------------------------------


def new_workspace_id() -> str:
    return secrets.token_urlsafe(16)


def sign_workspace(workspace_id: str) -> str:
    mac = hmac.new(
        settings.session_secret.encode(), workspace_id.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{workspace_id}.{mac}"


def verify_workspace(cookie_value: str | None) -> str | None:
    """Return the workspace id only if the signature validates."""
    if not cookie_value or "." not in cookie_value:
        return None
    workspace_id, _, mac = cookie_value.rpartition(".")
    if not workspace_id or not mac:
        return None
    expected = hmac.new(
        settings.session_secret.encode(), workspace_id.encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(mac, expected):
        return None
    return workspace_id


# --- upload validation -------------------------------------------------------


def sniff_kind(data: bytes) -> str:
    """Identify the format from magic bytes. The declared Content-Type and the
    file extension are both attacker-controlled and are not consulted."""
    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(ZIP_MAGIC):
        # DOCX is a zip; confirm the Word-specific part exists.
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
            if "word/document.xml" in names:
                return "docx"
        except zipfile.BadZipFile:
            raise UploadRejected("Berkas zip rusak atau tidak bisa dibaca.")
        raise UploadRejected(
            "Berkas zip ini bukan DOCX. Format yang didukung: PDF dan DOCX."
        )
    raise UploadRejected("Format tidak didukung. Unggah PDF atau DOCX.")


def check_zip_bomb(data: bytes) -> None:
    """Reject archives whose uncompressed size dwarfs their compressed size."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            uncompressed = sum(i.file_size for i in zf.infolist())
    except zipfile.BadZipFile:
        raise UploadRejected("Berkas zip rusak atau tidak bisa dibaca.")
    if uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise UploadRejected("Isi berkas terlalu besar setelah dibuka.")
    if len(data) and uncompressed / len(data) > MAX_DECOMPRESSION_RATIO:
        raise UploadRejected(
            "Berkas ditolak: rasio kompresinya tidak wajar "
            "(indikasi decompression bomb)."
        )


def safe_display_name(filename: str | None) -> str:
    """Sanitize for *display only*. The stored object is keyed by a generated
    UUID; this string never becomes a path component."""
    raw = (filename or "dokumen").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in " ._-()[]").strip()
    cleaned = cleaned.lstrip(".") or "dokumen"
    return cleaned[:120]


def validate_upload(filename: str | None, data: bytes) -> tuple[str, str, str]:
    """Returns (kind, display_name, sha256). Raises UploadRejected on failure."""
    if not data:
        raise UploadRejected("Berkas kosong.")
    if len(data) > settings.max_file_bytes:
        raise UploadRejected(
            f"Berkas melebihi batas {settings.max_file_mb} MB "
            f"(ukurannya {len(data) / 1024 / 1024:.1f} MB)."
        )
    kind = sniff_kind(data)
    if kind == "docx":
        check_zip_bomb(data)
    return kind, safe_display_name(filename), hashlib.sha256(data).hexdigest()
