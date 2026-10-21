"""Evaluate retrieval and answers on the four-document SOP corpus.

    cd api
    uv run python -m eval.run --retrieval-only        # no LLM calls, runs offline
    uv run python -m eval.run                         # retrieval + answers (needs GEMINI_API_KEY or GROQ_API_KEY)

Retrieval is scored for four settings so the value of each stage is visible:
dense only, BM25 only, dense + BM25 fused with RRF, and the production path
(fusion to 30 candidates, then the cross-encoder reranks to 8). Answers are
generated with the real prompt and checked by the real citation guard.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The app reads its settings once, at import. Point the vector store at a
# throwaway folder before anything from app.* is imported.
QDRANT_DIR = HERE / ".qdrant"
os.environ["QDRANT_PATH"] = str(QDRANT_DIR)
os.environ.pop("QDRANT_URL", None)

from qdrant_client import models  # noqa: E402

from app.config import settings  # noqa: E402
from app.ingest.parse_docx import parse_docx  # noqa: E402
from app.llm.base import Message, StreamOutcome, TransientProviderError, build_chain  # noqa: E402
from app.rag import citation_guard, embed, generate, retrieve, store  # noqa: E402
from app.rag.store import DENSE, SPARSE, client, workspace_filter  # noqa: E402
from eval import corpus  # noqa: E402
from eval.metrics import (  # noqa: E402
    abstained,
    answer_correct,
    gold_rank,
    is_gold,
    latency_summary,
    retrieval_summary,
)

WORKSPACE = "eval-workspace"
TOP_K = 8
CACHE_FILE = HERE / ".cache" / "answers.json"
RESULTS_DIR = HERE / "results"

MODES = ["dense", "bm25", "rrf", "rrf_rerank"]
MODE_LABEL = {
    "dense": "Dense only",
    "bm25": "BM25 only",
    "rrf": "Dense + BM25 (RRF)",
    "rrf_rerank": "RRF + cross-encoder (production)",
}


def ingest() -> dict[str, int]:
    """Fresh index of the corpus. Returns chunks per document."""
    client.cache_clear() if hasattr(client, "cache_clear") else None
    if QDRANT_DIR.exists():
        shutil.rmtree(QDRANT_DIR)
    counts: dict[str, int] = {}
    for name, data in corpus.documents().items():
        parsed = parse_docx(data)
        counts[name] = store.upsert_chunks(WORKSPACE, name.rsplit(".", 1)[0], name, parsed.chunks)
    return counts


def _payload_rows(points) -> list[tuple[str, list[str]]]:
    return [((p.payload or {}).get("doc_name", ""), (p.payload or {}).get("heading_path") or []) for p in points]


def rank_lists(query: str) -> dict[str, list[tuple[str, list[str]]]]:
    dense_vec, sparse_vec = embed.embed_query(query)
    flt = workspace_filter(WORKSPACE)
    c = client()
    dense = c.query_points(
        collection_name=settings.collection, query=dense_vec, using=DENSE,
        limit=TOP_K, query_filter=flt, with_payload=True,
    ).points
    bm25 = c.query_points(
        collection_name=settings.collection, query=models.SparseVector(**sparse_vec), using=SPARSE,
        limit=TOP_K, query_filter=flt, with_payload=True,
    ).points
    fused = c.query_points(
        collection_name=settings.collection,
        prefetch=[
            models.Prefetch(query=dense_vec, using=DENSE, limit=settings.top_k_dense, filter=flt),
            models.Prefetch(query=models.SparseVector(**sparse_vec), using=SPARSE, limit=settings.top_k_sparse, filter=flt),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=TOP_K, with_payload=True,
    ).points
    production = retrieve.retrieve(WORKSPACE, query)
    return {
        "dense": _payload_rows(dense),
        "bm25": _payload_rows(bm25),
        "rrf": _payload_rows(fused),
        "rrf_rerank": [(ch.doc_name, ch.heading_path) for ch in production],
    }


def cache_key(question: str, chunks) -> str:
    material = "|".join([
        settings.llm_provider, settings.gemini_model, settings.groq_model,
        generate.SYSTEM_PROMPT, question, generate.format_context(chunks),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    return json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


async def _answer(question: str, chunks, lang: str) -> tuple[str, StreamOutcome]:
    outcome = StreamOutcome()
    parts: list[str] = []
    async for piece in generate.stream_answer(question, chunks, [], outcome, lang):
        parts.append(piece)
    return "".join(parts), outcome


def generate_answer(question: str, chunks, lang: str, use_cache: bool, cache: dict, pace: float) -> dict:
    key = cache_key(question, chunks)
    if use_cache and key in cache:
        return {**cache[key], "cached": True}
    last_error = ""
    for attempt in range(1, 5):
        started = time.perf_counter()
        try:
            text, outcome = asyncio.run(_answer(question, chunks, lang))
            record = {
                "text": text,
                "provider": outcome.provider,
                "failed_over_from": outcome.failed_over_from,
                "latency_s": round(time.perf_counter() - started, 2),
            }
            cache[key] = record
            save_cache(cache)
            time.sleep(pace)
            return {**record, "cached": False}
        except TransientProviderError as exc:
            last_error = str(exc)
            wait = 20 * attempt
            print(f"    rate limited, waiting {wait}s (attempt {attempt})", file=sys.stderr)
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001 - a bad key or model must not abort the whole run
            last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            print(f"    provider error, skipping this question: {last_error}", file=sys.stderr)
            break
    return {"text": "", "provider": "", "failed_over_from": None, "latency_s": None, "cached": False, "error": last_error}


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true", help="skip LLM answers")
    parser.add_argument("--no-cache", action="store_true", help="ignore cached answers")
    parser.add_argument("--pace", type=float, default=5.0, help="seconds between LLM calls")
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions")
    parser.add_argument("--out", default=str(RESULTS_DIR / "latest.json"))
    args = parser.parse_args()

    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[: args.limit]

    print("Indexing corpus ...")
    chunk_counts = ingest()
    print("  " + ", ".join(f"{n}: {c} chunks" for n, c in chunk_counts.items()))
    retrieve.warm()

    answerable = [q for q in questions if q.get("gold")]
    ranks: dict[str, dict[str, int | None]] = {m: {} for m in MODES}
    print(f"Retrieval on {len(answerable)} answerable questions ...")
    retrieved_by_q: dict[str, list] = {}
    for q in answerable:
        lists = rank_lists(q["q"])
        for mode in MODES:
            ranks[mode][q["id"]] = gold_rank(lists[mode], q["gold"])
        retrieved_by_q[q["id"]] = lists["rrf_rerank"]

    retrieval = {
        mode: {
            "overall": retrieval_summary(list(ranks[mode].values())),
            "by_category": {
                cat: retrieval_summary([ranks[mode][q["id"]] for q in answerable if q["category"] == cat])
                for cat in sorted({q["category"] for q in answerable})
            },
        }
        for mode in MODES
    }

    answers: list[dict] = []
    if not args.retrieval_only:
        cache = {} if args.no_cache else load_cache()
        print(f"Answers for {len(questions)} questions ({settings.llm_provider}, fallback {settings.llm_fallback_provider}) ...")
        for i, q in enumerate(questions, start=1):
            chunks = retrieve.retrieve(WORKSPACE, q["q"])
            result = generate_answer(q["q"], chunks, q["lang"], not args.no_cache, cache, args.pace)
            guard = citation_guard.validate(result["text"], chunks)
            cited_gold = any(is_gold(c.doc_name, c.heading_path, q.get("gold")) for c in guard.citations)
            record = {
                "id": q["id"], "category": q["category"], "question": q["q"], "answer": result["text"],
                "provider": result["provider"], "latency_s": result["latency_s"],
                "citations_accepted": guard.accepted, "citations_rejected": guard.rejected,
                "cited_gold": cited_gold if q.get("gold") else None,
                "gold_in_context": any(is_gold(ch.doc_name, ch.heading_path, q.get("gold")) for ch in chunks) if q.get("gold") else None,
            }
            if "error" in result:
                record["error"] = result["error"]
            if q.get("expect_abstain"):
                record["abstained"] = abstained(result["text"])
                record["correct"] = record["abstained"]
            else:
                record["abstained"] = abstained(result["text"])
                record["correct"] = bool(result["text"]) and answer_correct(result["text"], q["must"], q.get("forbid"))
            answers.append(record)
            flag = "ok " if record["correct"] else "MISS"
            print(f"  [{i:02d}/{len(questions)}] {flag} {q['id']} ({record['provider'] or '-'}, {record['latency_s']}s)")

    summary: dict = {"corpus": chunk_counts, "questions": len(questions), "answerable": len(answerable), "retrieval": retrieval}
    if answers:
        ans = [a for a in answers if a["category"] != "not_in_doc"]
        neg = [a for a in answers if a["category"] == "not_in_doc"]
        by_cat: dict[str, list] = defaultdict(list)
        for a in ans:
            by_cat[a["category"]].append(a["correct"])
        cited = [a for a in ans if a["citations_accepted"] + a["citations_rejected"] > 0]
        summary["answers"] = {
            "answerable_correct": f"{sum(a['correct'] for a in ans)}/{len(ans)}",
            "answerable_correct_rate": round(sum(a["correct"] for a in ans) / len(ans), 3) if ans else None,
            "by_category": {c: f"{sum(v)}/{len(v)}" for c, v in sorted(by_cat.items())},
            "false_abstentions": sum(1 for a in ans if a["abstained"] and not a["correct"]),
            "not_in_doc_abstained": f"{sum(a['abstained'] for a in neg)}/{len(neg)}",
            "answers_with_citations": f"{len(cited)}/{len(ans)}",
            "citations_accepted": sum(a["citations_accepted"] for a in answers),
            "citations_rejected": sum(a["citations_rejected"] for a in answers),
            "cited_gold_section": f"{sum(1 for a in ans if a['cited_gold'])}/{len(ans)}",
            "gold_in_context": f"{sum(1 for a in ans if a['gold_in_context'])}/{len(ans)}",
            "latency": latency_summary([a["latency_s"] for a in answers if a["latency_s"]]),
            "providers": {p or "none": sum(1 for a in answers if a["provider"] == p) for p in sorted({a["provider"] for a in answers})},
            "model": {"gemini": settings.gemini_model, "groq": settings.groq_model},
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "answers": answers}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRetrieval (answerable questions, top 8)")
    print(f"{'setting':36s} {'hit@1':>7s} {'hit@3':>7s} {'hit@8':>7s} {'MRR':>6s}")
    for mode in MODES:
        o = retrieval[mode]["overall"]
        print(f"{MODE_LABEL[mode]:36s} {pct(o['hit@1']):>7s} {pct(o['hit@3']):>7s} {pct(o['hit@8']):>7s} {o['mrr']:>6}")
    if "answers" in summary:
        print("\nAnswers:", json.dumps(summary["answers"], ensure_ascii=False, indent=1))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
