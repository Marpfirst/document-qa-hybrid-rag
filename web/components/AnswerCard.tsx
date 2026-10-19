"use client";

import AnswerText from "@/components/AnswerText";
import { useLang } from "@/lib/i18n";
import type { Citation } from "@/lib/api";

export type Phase = "retrieving" | "composing" | "streaming" | "done";

const STEP_KEYS = ["stepRetrieve", "stepRank", "stepRerank", "stepAnswer"] as const;

/** How far the pipeline has actually got, from real SSE events. */
function stepIndex(phase: Phase): number {
  // The retrieval event covers fetch + fusion + rerank in one server round
  // trip, so those three land together rather than ticking one at a time.
  if (phase === "retrieving") return 0;
  return 3;
}

function Check() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="10"
      height="10"
      fill="none"
      stroke="currentColor"
      strokeWidth="3.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m20 6-11 11-5-5" />
    </svg>
  );
}

function Stepper({ phase, contextCount }: { phase: Phase; contextCount?: number }) {
  const { t } = useLang();
  const reached = stepIndex(phase);
  const answering = phase !== "retrieving";

  return (
    <div className="border-b border-line bg-bg/60 p-4 sm:p-5">
      <p className="mb-3 text-xs font-medium">
{answering ? t.composing : t.searching}
      </p>
      <ol className="flex items-center gap-1.5 text-[11px] font-medium">
        {STEP_KEYS.map((stepKey, index) => {
          const done = index < reached || (index === 3 && phase === "done");
          const active = index === reached && !done;
          // Middle steps are noise on a narrow screen; the ends carry the story.
          const hideOnMobile = index === 1 || index === 2;

          return (
            <li
              key={stepKey}
              className={`flex min-w-0 items-center gap-1.5 ${
                hideOnMobile ? "hidden sm:flex" : "flex"
              } ${index > 0 ? "flex-1" : ""}`}
            >
              {index > 0 && (
                <span
                  aria-hidden="true"
                  className={`h-px min-w-2 flex-1 ${done || active ? "bg-cite/40" : "bg-line"}`}
                />
              )}
              <span
                aria-hidden="true"
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${
                  done
                    ? "bg-cite text-white"
                    : active
                      ? "animate-pulse-soft border-2 border-accent"
                      : "border-2 border-line"
                }`}
              >
                {done && <Check />}
              </span>
              <span
                className={`truncate ${
                  done ? "text-cite" : active ? "text-accent" : "text-ink-soft"
                }`}
              >
                {t[stepKey]}
              </span>
            </li>
          );
        })}
      </ol>
      {contextCount != null && (
        <p className="mt-3 text-[10px] text-ink-soft">
          {contextCount} {t.chunksFound}
        </p>
      )}
    </div>
  );
}

interface Props {
  content: string;
  citations: Citation[];
  phase: Phase;
  contextCount?: number;
  provider?: string;
  failedOverFrom?: string | null;
  rejected?: number;
  docCount?: number;
}

export default function AnswerCard({
  content,
  citations,
  phase,
  contextCount,
  provider,
  failedOverFrom,
  rejected,
  docCount,
}: Props) {
  const { t } = useLang();

  return (
    <div className="overflow-hidden rounded-2xl rounded-tl-sm border border-line bg-surface">
      {phase !== "done" && (
        <Stepper phase={phase} contextCount={contextCount} />
      )}

      {content && (
        <div className="p-4 text-[15px] leading-7 sm:p-5">
          <AnswerText text={content} citations={citations} />
        </div>
      )}

      {phase === "done" && (
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 border-t border-line bg-bg/60 px-4 py-3 text-[11px] text-ink-soft sm:px-5">
          <span>
            {t.source}{" "}
            <strong className="font-medium text-ink">
              {contextCount ?? 0} {t.chunks}
              {docCount ? ` ${t.fromDocs} ${docCount} ${t.docsWord}` : ""}
            </strong>
          </span>
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            {(rejected ?? 0) > 0 && (
              <span
                title="Model menyebut sumber yang tidak ada di konteks; penanda itu dibuang server."
                className="rounded bg-warn-soft px-1.5 py-0.5 text-warn"
              >
                {rejected} {t.rejected}
              </span>
            )}
            {failedOverFrom && (
              <span className="rounded bg-warn-soft px-1.5 py-0.5 text-warn">
                {failedOverFrom} {t.failedOver}
              </span>
            )}
            {provider && (
              <span>
                {t.model}{" "}
                <strong className="font-medium text-ink">{provider}</strong>
              </span>
            )}
          </span>
        </div>
      )}
    </div>
  );
}
