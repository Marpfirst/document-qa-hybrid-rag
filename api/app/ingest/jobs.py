"""In-process ingest jobs and their status.

Deliberately not Redis + a worker process: one process handles demo load, and
a reliable free Redis is scarce. The trade-off is real and documented — job
state lives in memory, so a restart loses in-flight jobs. Indexed chunks
survive in Qdrant; only the status record is lost.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from app.config import settings
from app.ingest.parse_docx import parse_docx
from app.ingest.parse_pdf import ParseError, parse_pdf
from app.rag import store
from app.schemas import DocumentSummary, JobStatus


@dataclass
class DocumentRecord:
    doc_id: str
    doc_name: str
    workspace_id: str
    sha256: str
    kind: str
    status: JobStatus = "queued"
    chunks: int = 0
    pages_total: int = 0
    pages_indexed: int = 0
    pages_skipped: int = 0
    note: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)

    def to_summary(self) -> DocumentSummary:
        return DocumentSummary(
            doc_id=self.doc_id,
            doc_name=self.doc_name,
            status=self.status,
            chunks=self.chunks,
            pages_total=self.pages_total,
            pages_indexed=self.pages_indexed,
            pages_skipped=self.pages_skipped,
            note=self.note,
            error=self.error,
        )


class DocumentRegistry:
    def __init__(self) -> None:
        self._by_workspace: dict[str, dict[str, DocumentRecord]] = {}
        self._lock = threading.Lock()

    def _bucket(self, workspace_id: str) -> dict[str, DocumentRecord]:
        return self._by_workspace.setdefault(workspace_id, {})

    def prune(self, workspace_id: str) -> None:
        """Drop records past the workspace TTL so counts stay honest."""
        cutoff = time.time() - settings.workspace_ttl_hours * 3600
        bucket = self._bucket(workspace_id)
        for doc_id in [k for k, v in bucket.items() if v.created_at < cutoff]:
            bucket.pop(doc_id, None)

    def list(self, workspace_id: str) -> list[DocumentRecord]:
        with self._lock:
            self.prune(workspace_id)
            return sorted(
                self._bucket(workspace_id).values(), key=lambda r: r.created_at
            )

    def get(self, workspace_id: str, doc_id: str) -> DocumentRecord | None:
        with self._lock:
            return self._bucket(workspace_id).get(doc_id)

    def find_by_hash(self, workspace_id: str, sha256: str) -> DocumentRecord | None:
        with self._lock:
            self.prune(workspace_id)
            for record in self._bucket(workspace_id).values():
                if record.sha256 == sha256 and record.status != "failed":
                    return record
        return None

    def active_count(self, workspace_id: str) -> int:
        with self._lock:
            self.prune(workspace_id)
            return sum(
                1
                for r in self._bucket(workspace_id).values()
                if r.status != "failed"
            )

    def add(
        self, workspace_id: str, doc_name: str, sha256: str, kind: str
    ) -> DocumentRecord:
        record = DocumentRecord(
            doc_id=uuid.uuid4().hex,
            doc_name=doc_name,
            workspace_id=workspace_id,
            sha256=sha256,
            kind=kind,
        )
        with self._lock:
            self._bucket(workspace_id)[record.doc_id] = record
        return record

    def remove(self, workspace_id: str, doc_id: str) -> bool:
        with self._lock:
            return self._bucket(workspace_id).pop(doc_id, None) is not None


registry = DocumentRegistry()


def run_ingest(record: DocumentRecord, data: bytes) -> None:
    """Parse, chunk, embed, and index. Runs in a background task."""
    try:
        record.status = "parsing"
        parsed = (
            parse_pdf(data) if record.kind == "pdf" else parse_docx(data)
        )

        record.pages_total = parsed.pages_total
        record.pages_indexed = parsed.pages_digital + parsed.pages_ocr_done
        record.pages_skipped = (
            parsed.pages_scanned + parsed.pages_broken + parsed.pages_blank
        )
        record.note = parsed.skipped_note()

        if not parsed.chunks:
            record.status = "failed"
            record.error = (
                record.note
                or "Tidak ada teks yang bisa dibaca dari dokumen ini."
            )
            return

        record.status = "embedding"
        record.chunks = store.upsert_chunks(
            record.workspace_id, record.doc_id, record.doc_name, parsed.chunks
        )
        record.status = "ready"
    except ParseError as exc:
        record.status = "failed"
        record.error = str(exc)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a job error
        record.status = "failed"
        record.error = f"Gagal memproses dokumen: {exc}"
