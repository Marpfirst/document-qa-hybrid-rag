export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type JobStatus = "queued" | "parsing" | "embedding" | "ready" | "failed";

export interface DocumentSummary {
  doc_id: string;
  doc_name: string;
  status: JobStatus;
  chunks: number;
  pages_total: number;
  pages_indexed: number;
  pages_skipped: number;
  note: string | null;
  error: string | null;
}

export interface RetrievedChunk {
  ref: number;
  doc_name: string;
  heading_path: string[];
  page: number | null;
  text: string;
  dense_score: number | null;
  sparse_score: number | null;
  fusion_score: number | null;
  rerank_score: number | null;
  is_ocr: boolean;
}

export interface Citation {
  ref: number;
  doc_name: string;
  heading_path: string[];
  page: number | null;
  quote: string;
  is_ocr: boolean;
}

/** Credentials must be included: the workspace lives in an HttpOnly cookie. */
const fetchOptions: RequestInit = { credentials: "include" };

export async function listDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API_BASE}/documents`, fetchOptions);
  if (!res.ok) throw new Error("Gagal memuat daftar dokumen.");
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_BASE}/documents`, {
    ...fetchOptions,
    method: "POST",
    body,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unggahan ditolak.");
  }
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    ...fetchOptions,
    method: "DELETE",
  });
  if (!res.ok && res.status !== 404) throw new Error("Gagal menghapus dokumen.");
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, fetchOptions);
    return res.ok;
  } catch {
    return false;
  }
}

export interface StreamHandlers {
  onRetrieval?: (chunks: RetrievedChunk[]) => void;
  onDelta?: (text: string) => void;
  onCitations?: (citations: Citation[], rejected: number) => void;
  onDone?: (info: {
    provider?: string;
    failed_over_from?: string | null;
    /** Server-validated answer: fabricated [doc:N] markers already stripped. */
    clean_text?: string;
  }) => void;
  onError?: (message: string) => void;
}

/**
 * Consume the SSE answer stream.
 *
 * Uses fetch + a manual parser rather than EventSource because EventSource
 * cannot issue POST requests or send a body.
 */
export async function streamChat(
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
  handlers: StreamHandlers,
  /** UI language; decides the language of server-written replies. */
  lang: "ID" | "EN" = "ID",
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    ...fetchOptions,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, lang }),
    signal,
  });

  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => null);
    handlers.onError?.(detail?.detail ?? "Server tidak merespons.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(dataLines.join("\n"));
      } catch {
        continue;
      }

      switch (event) {
        case "retrieval":
          handlers.onRetrieval?.((payload.chunks ?? []) as RetrievedChunk[]);
          break;
        case "delta":
          handlers.onDelta?.(payload.text as string);
          break;
        case "citation":
          handlers.onCitations?.(
            (payload.citations ?? []) as Citation[],
            (payload.rejected ?? 0) as number,
          );
          break;
        case "error":
          handlers.onError?.(payload.message as string);
          break;
        case "done":
          handlers.onDone?.(
            payload as { provider?: string; clean_text?: string },
          );
          break;
      }
    }
  }
}
