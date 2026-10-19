"""Hybrid retrieval: dense + BM25, fused with RRF, then reranked.

Dense search alone misses the things SOP questions most often hinge on —
document codes ("SOP-HR-014"), exact figures, abbreviations — because an
embedding generalizes them away. BM25 alone misses paraphrase. RRF fuses the
two ranked lists without needing hand-tuned weights, and the cross-encoder
then reads query and candidate *together* to produce the final ordering.

The workspace filter is applied to **both** prefetch branches. Filtering only
the fused result would let one branch surface another tenant's documents.
"""

from __future__ import annotations

import threading
from functools import lru_cache

from qdrant_client import models

from app.config import settings
from app.rag import embed
from app.rag.store import DENSE, SPARSE, client, ensure_collection, workspace_filter
from app.schemas import RetrievedChunk

_rerank_lock = threading.Lock()


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.rerank_model)


def warm() -> None:
    _reranker()


def _payload_to_chunk(ref: int, payload: dict, fusion_score: float) -> RetrievedChunk:
    return RetrievedChunk(
        ref=ref,
        doc_name=payload.get("doc_name", "dokumen"),
        heading_path=payload.get("heading_path") or [],
        page=payload.get("page"),
        text=payload.get("text", ""),
        fusion_score=fusion_score,
        is_ocr=bool(payload.get("is_ocr")),
    )


def _score_branches(
    workspace_id: str, dense_vec: list[float], sparse_vec: dict
) -> tuple[dict[str, float], dict[str, float]]:
    """Per-branch scores, used only to populate the trace panel.

    The fused query does not expose which branch contributed what, and being
    able to see dense vs sparse contribution separately is the fastest way to
    catch a silently broken BM25 index.
    """
    c = client()
    flt = workspace_filter(workspace_id)
    dense_scores: dict[str, float] = {}
    sparse_scores: dict[str, float] = {}
    try:
        dense_hits = c.query_points(
            collection_name=settings.collection,
            query=dense_vec,
            using=DENSE,
            limit=settings.top_k_dense,
            query_filter=flt,
            with_payload=False,
        ).points
        dense_scores = {str(p.id): float(p.score) for p in dense_hits}

        sparse_hits = c.query_points(
            collection_name=settings.collection,
            query=models.SparseVector(**sparse_vec),
            using=SPARSE,
            limit=settings.top_k_sparse,
            query_filter=flt,
            with_payload=False,
        ).points
        sparse_scores = {str(p.id): float(p.score) for p in sparse_hits}
    except Exception:
        pass
    return dense_scores, sparse_scores


def retrieve(workspace_id: str, query: str) -> list[RetrievedChunk]:
    ensure_collection()
    dense_vec, sparse_vec = embed.embed_query(query)
    flt = workspace_filter(workspace_id)

    fused = client().query_points(
        collection_name=settings.collection,
        prefetch=[
            models.Prefetch(
                query=dense_vec,
                using=DENSE,
                limit=settings.top_k_dense,
                filter=flt,  # both branches must be filtered
            ),
            models.Prefetch(
                query=models.SparseVector(**sparse_vec),
                using=SPARSE,
                limit=settings.top_k_sparse,
                filter=flt,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=settings.fusion_limit,
        with_payload=True,
    ).points

    if not fused:
        return []

    dense_scores, sparse_scores = _score_branches(workspace_id, dense_vec, sparse_vec)

    candidates = [
        _payload_to_chunk(0, point.payload or {}, float(point.score))
        for point in fused
    ]
    for candidate, point in zip(candidates, fused):
        pid = str(point.id)
        candidate.dense_score = dense_scores.get(pid)
        candidate.sparse_score = sparse_scores.get(pid)

    ranked = _rerank(query, candidates)
    top = ranked[: settings.rerank_to]
    for index, chunk in enumerate(top, start=1):
        chunk.ref = index
    return top


def _rerank(query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Cross-encoder rerank. Falls back to fusion order if the model fails,
    because a degraded ordering is far better than a failed request."""
    if len(candidates) <= 1:
        return candidates
    pairs = [
        (query, " > ".join(c.heading_path + [c.text]) if c.heading_path else c.text)
        for c in candidates
    ]
    try:
        with _rerank_lock:
            scores = _reranker().predict(pairs)
    except Exception:
        return candidates
    for candidate, score in zip(candidates, scores):
        candidate.rerank_score = float(score)
    return sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)
