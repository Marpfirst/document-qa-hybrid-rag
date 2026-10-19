"""Dense + sparse embeddings, both running locally on CPU.

The E5 model family requires asymmetric prefixes: "query: " when embedding a
search query, "passage: " when embedding indexed text. Getting this wrong
degrades retrieval silently — no error, just worse results. Symmetric models
(paraphrase-*, LaBSE) must NOT get those prefixes, or quality drops the same
way. Both decisions live here so there is exactly one place to get it right.
"""

from __future__ import annotations

import threading
from functools import lru_cache

from fastembed import SparseTextEmbedding, TextEmbedding

from app.config import settings

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

_lock = threading.Lock()


def needs_e5_prefix(model_name: str | None = None) -> bool:
    return "e5" in (model_name or settings.dense_model).lower()


@lru_cache(maxsize=1)
def _dense() -> TextEmbedding:
    return TextEmbedding(model_name=settings.dense_model)


@lru_cache(maxsize=1)
def _sparse() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=settings.sparse_model)


def warm() -> None:
    """Download and load both models so the first upload doesn't pay the
    download cost while a user watches a progress bar."""
    with _lock:
        _dense()
        _sparse()


def _to_sparse(embedding) -> dict:
    return {
        "indices": [int(i) for i in embedding.indices],
        "values": [float(v) for v in embedding.values],
    }


def embed_passages(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    """Embed text destined for the index."""
    if not texts:
        return [], []
    dense_input = [PASSAGE_PREFIX + t for t in texts] if needs_e5_prefix() else texts
    with _lock:
        dense = [list(map(float, v)) for v in _dense().embed(dense_input)]
        sparse = [_to_sparse(v) for v in _sparse().embed(texts)]
    return dense, sparse


def embed_query(text: str) -> tuple[list[float], dict]:
    """Embed a user query. Note the different prefix from embed_passages."""
    dense_input = QUERY_PREFIX + text if needs_e5_prefix() else text
    with _lock:
        dense = list(map(float, next(iter(_dense().embed([dense_input])))))
        sparse = _to_sparse(next(iter(_sparse().embed([text]))))
    return dense, sparse
