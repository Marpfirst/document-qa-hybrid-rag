"""Tenant isolation: the failure mode that would be unrecoverable in public.

Two layers are checked. The storage layer must never return another
workspace's chunks even when the query matches perfectly. The HTTP layer must
derive the workspace from a signed cookie, so a caller cannot name someone
else's workspace and read it.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import retrieve, store
from app.schemas import Chunk
from app.security import sign_workspace, verify_workspace
from tests import fixtures

LEAVE_TEXT = "Cuti tahunan diberikan sebanyak 12 hari kerja per tahun."


@pytest.fixture(autouse=True)
def clean_store():
    store.ensure_collection()
    yield
    for ws in ("ws-alpha", "ws-beta"):
        for doc in ("doc-a", "doc-b"):
            store.delete_document(ws, doc)


def test_query_never_crosses_workspaces():
    store.upsert_chunks(
        "ws-alpha",
        "doc-a",
        "SOP Cuti.pdf",
        [Chunk(text=LEAVE_TEXT, heading_path=["4. Cuti"], page=3)],
    )

    mine = retrieve.retrieve("ws-alpha", "berapa hari cuti tahunan?")
    assert mine, "owner must be able to retrieve their own document"

    theirs = retrieve.retrieve("ws-beta", "berapa hari cuti tahunan?")
    assert theirs == [], "a different workspace must retrieve nothing"


def test_delete_is_scoped_to_the_owning_workspace():
    store.upsert_chunks("ws-alpha", "doc-a", "A.pdf", [Chunk(text=LEAVE_TEXT)])
    store.upsert_chunks("ws-beta", "doc-a", "B.pdf", [Chunk(text=LEAVE_TEXT)])

    store.delete_document("ws-alpha", "doc-a")

    assert store.count_chunks("ws-alpha") == 0
    assert store.count_chunks("ws-beta") == 1


def test_unsigned_or_tampered_cookie_is_rejected():
    good = sign_workspace("ws-alpha")
    assert verify_workspace(good) == "ws-alpha"

    assert verify_workspace("ws-alpha") is None, "unsigned value must not be trusted"
    assert verify_workspace("ws-alpha.deadbeef") is None, "bad MAC must be rejected"
    assert verify_workspace(None) is None

    # Swapping the id while keeping a valid-looking MAC must fail.
    _, _, mac = good.rpartition(".")
    assert verify_workspace(f"ws-beta.{mac}") is None


def test_http_client_cannot_read_another_sessions_documents():
    """End-to-end: a second visitor with a fresh cookie sees an empty workspace."""
    with TestClient(app) as alice:
        upload = alice.post(
            "/documents",
            files={
                "file": ("sop.docx", fixtures.sop_docx(), "application/octet-stream")
            },
        )
        assert upload.status_code == 202, upload.text
        doc_id = upload.json()["doc_id"]

        listing = alice.get("/documents").json()
        assert any(d["doc_id"] == doc_id for d in listing)

    with TestClient(app) as bob:
        assert bob.get("/documents").json() == []


def test_workspace_id_in_the_request_body_is_ignored():
    """The body is attacker-controlled; only the signed cookie decides."""
    with TestClient(app) as alice:
        alice.post(
            "/documents",
            files={
                "file": ("sop.docx", fixtures.sop_docx(), "application/octet-stream")
            },
        )
        alice_ws = verify_workspace(alice.cookies.get("kb_session"))
        assert alice_ws

    with TestClient(app) as bob:
        response = bob.post(
            "/chat/stream",
            json={"message": "berapa hari cuti tahunan?", "workspace_id": alice_ws},
        )
        assert response.status_code == 200
        body = response.text
        # Retrieval ran against Bob's own (empty) workspace.
        assert '"chunks": []' in body.replace("\n", " ") or "belum ada dokumen" in body.lower()
