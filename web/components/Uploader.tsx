"use client";

import { useCallback, useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  onUploaded: () => void;
  disabled?: boolean;
  disabledReason?: string;
}

export default function Uploader({ onUploaded, disabled, disabledReason }: Props) {
  const { t } = useLang();
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const send = useCallback(
    async (files: FileList | null) => {
      if (!files?.length || disabled) return;
      setBusy(true);
      setError(null);
      try {
        for (const file of Array.from(files)) {
          await uploadDocument(file);
        }
        onUploaded();
      } catch (err) {
        setError(err instanceof Error ? err.message : t.uploadFailed);
      } finally {
        setBusy(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [disabled, onUploaded, t],
  );

  const loadSample = useCallback(async () => {
    if (disabled) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/contoh-sop-cuti.docx");
      const blob = await res.blob();
      await uploadDocument(
        new File([blob], "contoh-sop-cuti.docx", { type: blob.type }),
      );
      onUploaded();
    } catch {
      setError(t.sampleFailed);
    } finally {
      setBusy(false);
    }
  }, [disabled, onUploaded, t]);

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void send(e.dataTransfer.files);
        }}
        className={`rounded-lg border border-dashed p-4 text-center transition-colors ${
          dragging
            ? "border-accent bg-accent-soft"
            : "border-line bg-surface"
        } ${disabled ? "opacity-55" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          multiple
          className="sr-only"
          id="file-input"
          disabled={disabled || busy}
          onChange={(e) => void send(e.target.files)}
        />
        <label
          htmlFor="file-input"
          className={`inline-block text-sm font-medium ${
            disabled || busy
              ? "cursor-not-allowed text-ink-soft"
              : "cursor-pointer text-accent underline underline-offset-4"
          }`}
        >
          {busy ? t.uploading : t.pickFile}
        </label>
        <p className="mt-1 text-xs text-ink-soft">
          {t.dropHint}
        </p>
      </div>

      {/* Visitors who won't upload their own SOP still need a way in. */}
      <button
        type="button"
        onClick={() => void loadSample()}
        disabled={disabled || busy}
        className="mt-2 w-full rounded-md border border-line bg-surface px-3 py-1.5 text-xs text-ink-soft hover:border-accent hover:text-accent disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-accent"
      >
        {t.useSample}
      </button>

      {disabled && disabledReason && (
        <p className="mt-2 text-xs text-ink-soft">{disabledReason}</p>
      )}
      {error && (
        <p className="mt-2 rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
