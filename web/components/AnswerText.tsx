"use client";

import { useState } from "react";
import type { Citation } from "@/lib/api";
import { useLang } from "@/lib/i18n";

// Mirrors the server-side pattern so multi-reference markers the model writes
// — [doc:1, doc:2], [doc:1;2] — render as chips instead of leaking raw text
// while streaming, before the validated copy replaces the whole answer.
const MARKER_SOURCE =
  String.raw`\[\s*doc:\s*\d+(?:\s*[,;]\s*(?:doc:\s*)?\d+)*\s*\]`;

function CitationPopover({ citation }: { citation: Citation }) {
  const { t } = useLang();
  return (
    <span
      role="dialog"
      className="absolute bottom-full left-0 z-20 mb-1.5 block w-72 rounded-lg border border-line bg-surface p-3 text-left shadow-lg"
    >
      <span className="flex items-baseline justify-between gap-2">
        <span className="truncate text-xs font-medium">{citation.doc_name}</span>
        {citation.is_ocr && (
          <span className="shrink-0 rounded bg-warn-soft px-1.5 py-0.5 text-[10px] text-warn">
            OCR
          </span>
        )}
      </span>
      {citation.heading_path.length > 0 && (
        <span className="mt-1 block text-[11px] text-ink-soft">
          {citation.heading_path.join(" › ")}
          {citation.page && ` · hal. ${citation.page}`}
        </span>
      )}
      <span className="mt-2 block border-l-2 border-cite pl-2 text-xs leading-relaxed text-ink-soft">
        {citation.quote}
      </span>
      {citation.is_ocr && (
        <span className="mt-2 block text-[10px] text-warn">
          {t.ocrWarning}
        </span>
      )}
    </span>
  );
}

// Models answer in Markdown whether asked to or not. Only the inline marks
// that actually show up get handled; parsing to React nodes rather than HTML
// keeps model output away from dangerouslySetInnerHTML.
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;

function renderInline(text: string, keyPrefix: string): React.JSX.Element[] {
  return text.split(INLINE).map((piece, index) => {
    const key = `${keyPrefix}-i${index}`;
    if (piece.startsWith("**") && piece.endsWith("**")) {
      return (
        <strong key={key} className="font-semibold text-ink">
          {piece.slice(2, -2)}
        </strong>
      );
    }
    if (piece.startsWith("`") && piece.endsWith("`")) {
      return (
        <code
          key={key}
          className="rounded bg-bg px-1 py-0.5 font-mono text-[0.85em]"
        >
          {piece.slice(1, -1)}
        </code>
      );
    }
    if (piece.startsWith("*") && piece.endsWith("*") && piece.length > 2) {
      return <em key={key}>{piece.slice(1, -1)}</em>;
    }
    return <span key={key}>{piece}</span>;
  });
}

/**
 * Renders answer text, turning [doc:N] markers into clickable citation chips.
 *
 * A marker is only rendered when its ref resolves against the server's
 * accepted-citation list; anything else is dropped rather than shown as text.
 */
export default function AnswerText({
  text,
  citations,
}: {
  text: string;
  citations: Citation[];
}) {
  const { t } = useLang();
  const [open, setOpen] = useState<number | null>(null);
  const byRef = new Map(citations.map((c) => [c.ref, c]));
  const isMarker = new RegExp(`^${MARKER_SOURCE}$`, "i");
  const splitter = new RegExp(`(${MARKER_SOURCE})`, "gi");

  const renderLine = (line: string, lineKey: string): React.JSX.Element[] =>
    line.split(splitter).flatMap((part, index): React.JSX.Element[] => {
      const key = `${lineKey}-${index}`;
      if (!isMarker.test(part)) return renderInline(part, key);

      const resolved = (part.match(/\d+/g) ?? [])
        .map(Number)
        .filter((ref) => byRef.has(ref));

      return resolved.map((ref) => (
        <span
          key={`${key}-${ref}`}
          className="relative inline-block align-baseline"
        >
          <button
            type="button"
            onClick={() => setOpen(open === ref ? null : ref)}
            aria-expanded={open === ref}
            aria-label={`${t.sourceLabel} ${ref}`}
            className="mx-0.5 rounded border border-cite-line bg-cite-soft px-1.5 py-0.5 align-baseline font-mono text-[11px] font-semibold text-cite transition-colors hover:brightness-95 focus-visible:outline-2 focus-visible:outline-cite"
          >
            {ref}
          </button>
          {open === ref && <CitationPopover citation={byRef.get(ref)!} />}
        </span>
      ));
    });

  // Group consecutive bullet lines into one list so they render as a list
  // rather than as stray asterisks on their own lines.
  const blocks: { type: "p" | "ul"; lines: string[] }[] = [];
  for (const line of text.split("\n")) {
    const bullet = /^\s*[*-]\s+(.*)$/.exec(line);
    const last = blocks[blocks.length - 1];
    if (bullet) {
      if (last?.type === "ul") last.lines.push(bullet[1]);
      else blocks.push({ type: "ul", lines: [bullet[1]] });
    } else if (last?.type === "p") {
      last.lines.push(line);
    } else {
      blocks.push({ type: "p", lines: [line] });
    }
  }

  return (
    <div className="relative flex flex-col gap-3">
      {blocks.map((block, blockIndex) =>
        block.type === "ul" ? (
          <ul
            key={blockIndex}
            className="flex list-outside list-disc flex-col gap-1.5 pl-5"
          >
            {block.lines.map((line, lineIndex) => (
              <li key={lineIndex}>{renderLine(line, `b${blockIndex}-${lineIndex}`)}</li>
            ))}
          </ul>
        ) : (
          <p key={blockIndex} className="whitespace-pre-wrap">
            {block.lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {lineIndex > 0 && "\n"}
                {renderLine(line, `b${blockIndex}-${lineIndex}`)}
              </span>
            ))}
          </p>
        ),
      )}
    </div>
  );
}
