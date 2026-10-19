from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from app.config import settings
from app.deps import WorkspaceSession, workspace_session
from app.ingest.jobs import registry, run_ingest
from app.rag import store
from app.ratelimit import limiter
from app.schemas import DocumentSummary, UploadAccepted
from app.security import UploadRejected, validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=UploadAccepted, status_code=202)
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    session: WorkspaceSession = Depends(workspace_session),
) -> UploadAccepted:
    if not settings.demo_enabled:
        raise HTTPException(503, "Demo sedang dinonaktifkan sementara.")

    data = await file.read()
    try:
        kind, display_name, sha256 = validate_upload(file.filename, data)
    except UploadRejected as exc:
        raise HTTPException(400, str(exc))

    # Re-uploading the same bytes is common and would otherwise pay the full
    # parse + embed cost again.
    existing = registry.find_by_hash(session.id, sha256)
    if existing:
        return UploadAccepted(
            doc_id=existing.doc_id,
            doc_name=existing.doc_name,
            status=existing.status,
            duplicate_of=existing.doc_id,
        )

    if registry.active_count(session.id) >= settings.max_files_per_workspace:
        raise HTTPException(
            400,
            f"Batas {settings.max_files_per_workspace} dokumen per ruang kerja "
            "sudah tercapai. Hapus salah satu dokumen dulu.",
        )

    record = registry.add(session.id, display_name, sha256, kind)
    background.add_task(run_ingest, record, data)
    return UploadAccepted(
        doc_id=record.doc_id, doc_name=record.doc_name, status=record.status
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    session: WorkspaceSession = Depends(workspace_session),
) -> list[DocumentSummary]:
    return [r.to_summary() for r in registry.list(session.id)]


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str, session: WorkspaceSession = Depends(workspace_session)
) -> None:
    record = registry.get(session.id, doc_id)
    if record is None:
        raise HTTPException(404, "Dokumen tidak ditemukan di ruang kerja ini.")
    store.delete_document(session.id, doc_id)
    registry.remove(session.id, doc_id)
