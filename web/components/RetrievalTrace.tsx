"use client";

import type { RetrievedChunk } from "@/lib/api";
import { useLang } from "@/lib/i18n";

/**
 * Shows what retrieval actually returned, per branch.
 *
 * Separating dense from sparse is not decoration: if the sparse column is
 * uniformly empty, the BM25 index is broken, and hybrid search has silently
 * degraded to dense-only without any error surfacing.
 */
/**
 * A score with a bar behind it.
 *
 * The raw numbers stay visible — they are the evidence — but the bar makes the
 * gap between branches readable at a glance, which is the actual question
 * ("did sparse contribute anything here?"), not the third decimal place.
 */
function ScoreRow({
  label,
  value,
  max,
  digits = 3,
  emphasis = false,
}: {
  label: string;
  value: number | null | undefined;
  max: number;
  digits?: number;
  emphasis?: boolean;
}) {
  const missing = value == null;
  // Scores can be negative (cross-encoder logits); shift so bars stay visible.
  const width = missing || max <= 0 ? 0 : Math.max(0, Math.min(1, value / max));

  return (
    <div className="flex items-center gap-1.5">
      <dt className="w-11 shrink-0 font-mono text-[10px] text-ink-soft">
        {label}
      </dt>
      <div
        className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-line"
        aria-hidden="true"
      >
        <div
          className={`h-full rounded-full ${emphasis ? "bg-cite" : "bg-cite/40"}`}
          style={{ width: `${width * 100}%` }}
        />
      </div>
      <dd
        className={`w-10 shrink-0 text-right font-mono text-[10px] tabular-nums ${
          missing ? "text-ink-soft opacity-40" : emphasis ? "font-semibold text-ink" : "text-ink-soft"
        }`}
      >
        {missing ? "—" : value.toFixed(digits)}
      </dd>
    </div>
  );
}

export default function RetrievalTrace({ chunks }: { chunks: RetrievedChunk[] }) {
  const { t } = useLang();
  if (!chunks.length) return null;

  // Normalise per result set, not against a fixed ceiling: the bars answer
  // "how does this chunk compare to the others retrieved", and the scales of
  // dense, sparse, RRF and rerank are not comparable to each other.
  const peak = (pick: (c: RetrievedChunk) => number | null | undefined) =>
    Math.max(...chunks.map((c) => pick(c) ?? 0), 0.0001);
  const maxDense = peak((c) => c.dense_score);
  const maxSparse = peak((c) => c.sparse_score);
  const maxFusion = peak((c) => c.fusion_score);
  const maxRerank = peak((c) => c.rerank_score);
  const sparseDead = chunks.every((c) => (c.sparse_score ?? 0) === 0);

  return (
    <section className="rounded-lg border border-line bg-surface">
      {sparseDead && (
        <p className="border-b border-line bg-warn-soft px-3 py-2 text-[11px] text-warn">
          {t.sparseDead}
        </p>
      )}

      <ol className="divide-y divide-line">
        {chunks.map((chunk) => (
          <li key={chunk.ref} className="px-3 py-2.5">
            <div className="flex items-baseline gap-2">
              <span className="rounded bg-cite-soft px-1.5 py-0.5 font-mono text-[11px] font-semibold text-cite">
                doc:{chunk.ref}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs" title={chunk.doc_name}>
                {chunk.doc_name}
              </span>
              {chunk.is_ocr && (
                <span className="rounded bg-warn-soft px-1.5 py-0.5 text-[10px] font-medium text-warn">
                  OCR
                </span>
              )}
            </div>

            {chunk.heading_path.length > 0 && (
              <p className="mt-1 text-[11px] text-ink-soft">
                {chunk.heading_path.join(" › ")}
                {chunk.page && ` · hal. ${chunk.page}`}
              </p>
            )}

            <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-ink-soft">
              {chunk.text}
            </p>

            <dl className="mt-2.5 flex flex-col gap-1">
              <ScoreRow label="dense" value={chunk.dense_score} max={maxDense} />
              <ScoreRow
                label="sparse"
                value={chunk.sparse_score}
                max={maxSparse}
                digits={2}
              />
              <ScoreRow label="rrf" value={chunk.fusion_score} max={maxFusion} />
              <ScoreRow
                label="rerank"
                value={chunk.rerank_score}
                max={maxRerank}
                digits={2}
                emphasis
              />
            </dl>
          </li>
        ))}
      </ol>
    </section>
  );
}
