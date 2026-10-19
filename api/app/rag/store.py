"""Qdrant access layer.

Single collection for all workspaces, isolated by a `workspace_id` payload
filter. Per-workspace collections would be cleaner conceptually but Qdrant
holds per-collection memory overhead — thousands of anonymous demo visitors
would exhaust RAM long before they exhaust disk.
"""

from __future__ import annotations

import threading
import time
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.config import settings
from app.rag import embed
from app.schemas import Chunk

DENSE = "dense"
SPARSE = "bm25"

_write_lock = threading.Lock()


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=settings.qdrant_path)


def ensure_collection() -> None:
    c = client()
    if not c.collection_exists(settings.collection):
        c.create_collection(
            collection_name=settings.collection,
            vectors_config={
                DENSE: models.VectorParams(
                    size=settings.dense_dim, distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={SPARSE: models.SparseVectorParams()},
        )
    # Without this index the workspace filter degrades to a full scan as data grows.
    for field in ("workspace_id", "doc_id", "expires_at"):
        try:
            c.create_payload_index(
                collection_name=settings.collection,
                field_name=field,
                field_schema=(
                    models.PayloadSchemaType.INTEGER
                    if field == "expires_at"
                    else models.PayloadSchemaType.KEYWORD
                ),
            )
        except Exception:
            pass  # already exists


def workspace_filter(workspace_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="workspace_id", match=models.MatchValue(value=workspace_id)
            )
        ]
    )


def upsert_chunks(
    workspace_id: str, doc_id: str, doc_name: str, chunks: list[Chunk]
) -> int:
    if not chunks:
        return 0
    ensure_collection()
    expires_at = int(time.time()) + settings.workspace_ttl_hours * 3600
    dense_vecs, sparse_vecs = embed.embed_passages([c.embedding_text() for c in chunks])

    points = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector={
                DENSE: dense_vecs[i],
                SPARSE: models.SparseVector(**sparse_vecs[i]),
            },
            payload={
                "workspace_id": workspace_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "heading_path": chunk.heading_path,
                "page": chunk.page,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "text": chunk.text,
                "is_ocr": chunk.is_ocr,
                "expires_at": expires_at,
            },
        )
        for i, chunk in enumerate(chunks)
    ]
    with _write_lock:
        client().upsert(collection_name=settings.collection, points=points, wait=True)
    return len(points)


def count_chunks(workspace_id: str, doc_id: str | None = None) -> int:
    ensure_collection()
    flt = workspace_filter(workspace_id)
    if doc_id:
        flt.must.append(
            models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
        )
    return client().count(
        collection_name=settings.collection, count_filter=flt, exact=True
    ).count


def delete_document(workspace_id: str, doc_id: str) -> None:
    ensure_collection()
    flt = workspace_filter(workspace_id)
    flt.must.append(
        models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
    )
    with _write_lock:
        client().delete(
            collection_name=settings.collection,
            points_selector=models.FilterSelector(filter=flt),
            wait=True,
        )


def sweep_expired() -> int:
    """Delete chunks past their TTL. This is what keeps demo storage bounded."""
    ensure_collection()
    now = int(time.time())
    flt = models.Filter(
        must=[models.FieldCondition(key="expires_at", range=models.Range(lt=now))]
    )
    before = client().count(
        collection_name=settings.collection, count_filter=flt, exact=True
    ).count
    if before:
        with _write_lock:
            client().delete(
                collection_name=settings.collection,
                points_selector=models.FilterSelector(filter=flt),
                wait=True,
            )
    return before
