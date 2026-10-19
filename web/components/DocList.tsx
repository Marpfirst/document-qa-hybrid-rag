"use client";

import { deleteDocument, type DocumentSummary, type JobStatus } from "@/lib/api";
import { useLang, type Dict } from "@/lib/i18n";

const STATUS_KEY: Record<JobStatus, keyof Dict> = {
  queued: "stQueued",
  parsing: "stParsing",
  embedding: "stEmbedding",
  ready: "stReady",
  failed: "stFailed",
};

function StatusPill({ status }: { status: JobStatus }) {
  const { t } = useLang();
  const tone =
    status === "ready"
      ? "bg-accent-soft text-accent"
      : status === "failed"
        ? "bg-danger-soft text-danger"
        : "bg-warn-soft text-warn";
  const working = status !== "ready" && status !== "failed";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${tone}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full bg-current ${working ? "animate-pulse-soft" : ""}`}
      />
      {t[STATUS_KEY[status]] as string}
    </span>
  );
}

interface Props {
  documents: DocumentSummary[];
  onChanged: () => void;
}

export default function DocList({ documents, onChanged }: Props) {
  const { t } = useLang();
  if (!documents.length) return null;

  return (
    <ul className="flex flex-col gap-2">
      {documents.map((doc) => (
        <li
          key={doc.doc_id}
          className="rounded-lg border border-line bg-surface p-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium" title={doc.doc_name}>
                {doc.doc_name}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <StatusPill status={doc.status} />
                {doc.status === "ready" && (
                  <span className="text-[11px] text-ink-soft tabular-nums">
                    {doc.chunks} {t.parts}
                    {doc.pages_total > 0 && ` · ${doc.pages_indexed}/${doc.pages_total} hal.`}
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                await deleteDocument(doc.doc_id);
                onChanged();
              }}
              className="shrink-0 rounded px-1.5 py-0.5 text-xs text-ink-soft hover:bg-danger-soft hover:text-danger focus-visible:outline-2 focus-visible:outline-accent"
              aria-label={`${t.remove} ${doc.doc_name}`}
            >
              {t.remove}
            </button>
          </div>

          {doc.note && (
            <p className="mt-2 rounded bg-warn-soft px-2 py-1.5 text-[11px] text-warn">
              {doc.note}
            </p>
          )}
          {doc.error && (
            <p className="mt-2 rounded bg-danger-soft px-2 py-1.5 text-[11px] text-danger">
              {doc.error}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
