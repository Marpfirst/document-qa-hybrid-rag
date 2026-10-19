"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AnswerCard, { type Phase } from "@/components/AnswerCard";
import { Icon } from "@/components/Icons";
import { useLang } from "@/lib/i18n";
import { useSpeechInput } from "@/lib/use-speech-input";
import { streamChat, type Citation, type RetrievedChunk } from "@/lib/api";
import type { StoredTurn } from "@/lib/conversations";

export interface Turn extends StoredTurn {
  phase?: Phase;
  docCount?: number;
}

interface Props {
  hasDocuments: boolean;
  turns: Turn[];
  onTurnsChange: (updater: (prev: Turn[]) => Turn[]) => void;
  onRetrieval: (chunks: RetrievedChunk[]) => void;
  onAttach: () => void;
}

export default function Chat({
  hasDocuments,
  turns,
  onTurnsChange,
  onRetrieval,
  onAttach,
}: Props) {
  const { lang, t } = useLang();
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const speech = useSpeechInput({
    onTranscript: useCallback((text: string) => setInput(text), []),
    lang: lang === "ID" ? "id-ID" : "en-US",
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || streaming || !hasDocuments) return;

    const history = turns
      .filter((t) => !t.error)
      .map((t) => ({ role: t.role, content: t.content }));

    onTurnsChange((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "", phase: "retrieving" },
    ]);
    setInput("");
    setStreaming(true);
    onRetrieval([]);

    const patchLast = (patch: Partial<Turn>) =>
      onTurnsChange((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], ...patch };
        return next;
      });

    await streamChat(trimmed, history, {
      onRetrieval: (chunks) => {
        onRetrieval(chunks);
        patchLast({
          phase: "composing",
          contextCount: chunks.length,
          docCount: new Set(chunks.map((c) => c.doc_name)).size,
        });
      },
      onDelta: (text) =>
        onTurnsChange((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          next[next.length - 1] = {
            ...last,
            content: last.content + text,
            phase: "streaming",
          };
          return next;
        }),
      onCitations: (citations, rejected) => patchLast({ citations, rejected }),
      onDone: (info) =>
        patchLast({
          provider: info.provider,
          failedOverFrom: info.failed_over_from ?? null,
          phase: "done",
          // Swap the streamed text for the server-validated version. The raw
          // stream can still contain fabricated [doc:N] markers; only this
          // copy has had them stripped, so it is what the user must end up
          // reading. Without this the citation guard protects the API response
          // but not the screen.
          ...(info.clean_text ? { content: info.clean_text } : {}),
        }),
      onError: (message) => patchLast({ error: message, phase: "done" }),
    }, lang);

    setStreaming(false);
    inputRef.current?.focus();
  }

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
          {turns.length === 0 ? (
            <div className="flex min-h-[45vh] flex-col justify-center">
              <h2 className="text-xl font-semibold tracking-tight text-balance sm:text-2xl">
                {t.emptyTitle}
              </h2>
              <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
{t.emptyBody}
              </p>

              {hasDocuments ? (
                <div className="mt-6">
                  <p className="text-xs font-medium text-ink-soft">
                    {t.examples}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {t.suggestions.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => void ask(s)}
                        className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={onAttach}
                  className="mt-6 self-start rounded-lg border border-dashed border-line px-3.5 py-2.5 text-xs text-ink-soft transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
                >
                  {t.uploadFirst}
                </button>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {turns.map((turn, index) =>
                turn.role === "user" ? (
                  <div key={index} className="flex justify-end">
                    <p className="max-w-[85%] rounded-2xl rounded-tr-sm bg-accent px-5 py-3 text-[15px] leading-relaxed text-white">
                      {turn.content}
                    </p>
                  </div>
                ) : (
                  <div key={index} className="max-w-[95%]">
                    {turn.error ? (
                      <p className="rounded-lg bg-danger-soft px-3.5 py-2.5 text-sm text-danger">
                        {turn.error}
                      </p>
                    ) : (
                      <AnswerCard
                        content={turn.content}
                        citations={turn.citations ?? []}
                        phase={turn.phase ?? "done"}
                        contextCount={turn.contextCount}
                        docCount={turn.docCount}
                        provider={turn.provider}
                        failedOverFrom={turn.failedOverFrom}
                        rejected={turn.rejected}
                      />
                    )}
                  </div>
                ),
              )}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="shrink-0 px-4 pb-4 sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void ask(input);
            }}
            className={`relative rounded-xl border bg-surface transition-colors ${
              speech.listening ? "border-accent" : "border-line focus-within:border-accent"
            }`}
          >
            <label htmlFor="question" className="sr-only">
              {t.placeholder}
            </label>
            <textarea
              id="question"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                // Enter sends; Shift+Enter is a newline, as in every chat app.
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void ask(input);
                }
              }}
              rows={2}
              placeholder={
                speech.listening
                  ? t.listening
                  : hasDocuments
                    ? t.placeholder
                    : t.placeholderEmpty
              }
              disabled={streaming || !hasDocuments}
              className="w-full resize-none bg-transparent px-4 pt-3.5 pb-11 text-sm outline-none disabled:opacity-60"
            />

            <div className="absolute bottom-2 left-2 flex items-center gap-0.5">
              <button
                type="button"
                onClick={onAttach}
                aria-label={t.attach}
                title={t.attachTitle}
                className="rounded-md p-2 text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
              >
                <Icon.Paperclip />
              </button>
              {/* Hidden where unsupported — a dead mic button is worse than
                  none, and the Web Speech API is Chrome/Edge only. */}
              {speech.supported && (
                <button
                  type="button"
                  onClick={speech.toggle}
                  disabled={streaming || !hasDocuments}
                  aria-pressed={speech.listening}
                  aria-label={speech.listening ? t.micOff : t.micOn}
                  title={t.micTitle}
                  className={`rounded-md p-2 transition-colors focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-40 ${
                    speech.listening
                      ? "animate-pulse-soft bg-accent-soft text-accent"
                      : "text-ink-soft hover:bg-accent-soft hover:text-accent"
                  }`}
                >
                  <Icon.Mic active={speech.listening} />
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={streaming || !input.trim()}
              aria-label={t.send}
              className="absolute right-2 bottom-2 rounded-lg bg-accent p-2.5 text-white transition-colors hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-40 disabled:hover:bg-accent"
            >
              <Icon.Send />
            </button>
          </form>

          {speech.error && (
            <p role="alert" className="mt-1.5 text-[11px] text-danger">
              {speech.error}
            </p>
          )}

          <p className="mt-2 text-center text-[10px] leading-relaxed text-ink-soft">
{t.disclaimer}
          </p>
        </div>
      </div>
    </>
  );
}
