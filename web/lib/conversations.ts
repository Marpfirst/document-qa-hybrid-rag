"use client";

import type { Citation } from "@/lib/api";

export interface StoredTurn {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  rejected?: number;
  provider?: string;
  failedOverFrom?: string | null;
  error?: string;
  contextCount?: number;
}

export interface Conversation {
  id: string;
  title: string;
  turns: StoredTurn[];
  updatedAt: number;
}

const KEY = "conversations";
const MAX = 20;

/**
 * Conversation history, kept in the browser.
 *
 * The API is stateless by design — documents are session-scoped and expire —
 * so history lives client-side rather than being faked from a server that
 * never stored it. Clearing site data clears the history, which matches what
 * the privacy note in the UI promises.
 */
export function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as Conversation[];
  } catch {
    return [];
  }
}

export function saveConversation(conversation: Conversation): Conversation[] {
  const rest = loadConversations().filter((c) => c.id !== conversation.id);
  const next = [conversation, ...rest]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* quota exceeded — history is a convenience, not load-bearing */
  }
  return next;
}

export function deleteConversation(id: string): Conversation[] {
  const next = loadConversations().filter((c) => c.id !== id);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  return next;
}

/** First question, trimmed — good enough as a label and always truthful. */
export function titleFrom(question: string): string {
  const clean = question.trim().replace(/\s+/g, " ");
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean;
}
