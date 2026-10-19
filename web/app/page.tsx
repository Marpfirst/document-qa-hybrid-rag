"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Chat, { type Turn } from "@/components/Chat";
import DocList from "@/components/DocList";
import { Icon } from "@/components/Icons";
import { AboutPage, HowItWorksPage } from "@/components/InfoPages";
import RetrievalTrace from "@/components/RetrievalTrace";
import Sidebar, { type NavKey } from "@/components/Sidebar";
import Uploader from "@/components/Uploader";
import {
  deleteConversation,
  loadConversations,
  saveConversation,
  titleFrom,
  type Conversation,
} from "@/lib/conversations";
import { useIsDesktop } from "@/lib/use-media-query";
import { useLang } from "@/lib/i18n";
import { useTheme } from "@/lib/use-theme";
import {
  checkHealth,
  listDocuments,
  type DocumentSummary,
  type RetrievedChunk,
} from "@/lib/api";

const MAX_DOCS = 3;

export default function Home() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [waking, setWaking] = useState(true);
  const [offline, setOffline] = useState(false);
  const [nav, setNav] = useState<NavKey>("chat");
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [railed, setRailed] = useState(false);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isDesktop = useIsDesktop();
  const { theme, toggle: toggleTheme } = useTheme();
  const { lang, t, toggle: toggleLang } = useLang();

  useEffect(() => {
    setMounted(true);
    setConversations(loadConversations());
  }, []);

  // Rails are inline columns on desktop but overlay drawers below `lg`, and a
  // drawer that opens itself on load covers the chat the visitor came for.
  useEffect(() => {
    if (!mounted) return;
    setLeftOpen(isDesktop);
    setRightOpen(isDesktop);
  }, [mounted, isDesktop]);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      /* transient; the poll will retry */
    }
  }, []);

  // The API sleeps when idle on a free host, and a cold start takes ~30s.
  // A bare spinner reads as "broken", so the wait is labelled explicitly.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await checkHealth();
      if (cancelled) return;
      setWaking(false);
      setOffline(!ok);
      if (ok) void refresh();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  // Ingest runs in the background; poll only while something is in flight.
  const pending = documents.some(
    (d) => d.status !== "ready" && d.status !== "failed",
  );
  useEffect(() => {
    if (!pending) {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
      return;
    }
    pollRef.current = setInterval(() => void refresh(), 1200);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pending, refresh]);

  const ready = useMemo(
    () => documents.filter((d) => d.status === "ready"),
    [documents],
  );
  const atCapacity = documents.length >= MAX_DOCS;

  // Persist once a turn settles, so a reload keeps finished answers but never
  // a half-streamed one.
  useEffect(() => {
    if (!turns.length) return;
    const last = turns[turns.length - 1];
    if (last.role !== "assistant" || (last.phase && last.phase !== "done")) {
      return;
    }
    const firstQuestion = turns.find((t) => t.role === "user")?.content ?? "";
    const id = currentId ?? crypto.randomUUID();
    if (!currentId) setCurrentId(id);
    setConversations(
      saveConversation({
        id,
        title: titleFrom(firstQuestion),
        turns,
        updatedAt: Date.now(),
      }),
    );
  }, [turns, currentId]);

  const newChat = () => {
    setTurns([]);
    setCurrentId(null);
    setChunks([]);
    setNav("chat");
    if (!isDesktop) setLeftOpen(false);
  };

  const openConversation = (id: string) => {
    const found = conversations.find((c) => c.id === id);
    if (!found) return;
    setTurns(found.turns);
    setCurrentId(id);
    setChunks([]);
    setNav("chat");
    if (!isDesktop) setLeftOpen(false);
  };

  const removeConversation = (id: string) => {
    setConversations(deleteConversation(id));
    if (id === currentId) newChat();
  };

  const goToUpload = () => {
    setNav("knowledge");
    if (!isDesktop) setLeftOpen(false);
  };

  const openLeft = () => {
    setLeftOpen(true);
    if (!isDesktop) setRightOpen(false);
  };
  const openRight = () => {
    setRightOpen(true);
    if (!isDesktop) setLeftOpen(false);
  };

  const knowledgePanel = (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
        {t.kbTitle}
      </h2>
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        {t.kbBody}
      </p>
      <div className="mt-6 flex flex-col gap-3">
        <Uploader
          onUploaded={refresh}
          disabled={atCapacity || offline}
          disabledReason={
            atCapacity ? t.atCapacity : undefined
          }
        />
        <DocList documents={documents} onChanged={refresh} />
      </div>
    </div>
  );

  return (
    <div className="relative flex h-dvh overflow-hidden">
      {/* Left rail: inline column on desktop, overlay drawer below lg. */}
      {leftOpen && !isDesktop && (
        <div
          className="fixed inset-0 z-30 bg-ink/25 motion-safe:animate-fade-in"
          onClick={() => setLeftOpen(false)}
          aria-hidden="true"
        />
      )}
      {leftOpen && (
        <aside
          id="sidebar"
          // min-w-0 + overflow-hidden are load-bearing: a flex item defaults to
          // min-width:auto, which pins the rail at its content width and makes
          // the w-20 class look like it does nothing.
          className={`z-40 min-w-0 shrink-0 overflow-hidden border-r border-line transition-[width] duration-300 ${
            isDesktop
              ? railed
                ? "w-20"
                : "w-64"
              : "w-64 fixed inset-y-0 left-0 shadow-2xl motion-safe:animate-slide-in"
          }`}
          {...(!isDesktop && { role: "dialog", "aria-modal": true, "aria-label": "Menu" })}
        >
          <Sidebar
            active={nav}
            onNavigate={(key) => {
              setNav(key);
              if (!isDesktop) setLeftOpen(false);
            }}
            conversations={conversations}
            currentId={currentId}
            onNewChat={newChat}
            onOpenConversation={openConversation}
            onDeleteConversation={removeConversation}
            readyCount={ready.length}
            collapsed={isDesktop && railed}
            onClose={isDesktop ? undefined : () => setLeftOpen(false)}
          />
        </aside>
      )}

      {/*
        Rendered outside the <aside> on purpose: the rail needs overflow-hidden
        to clip its labels while the width animates, and that would also clip
        this button, which deliberately overhangs the edge.
      */}
      {leftOpen && isDesktop && (
        <button
          type="button"
          onClick={() => setRailed((value) => !value)}
          aria-label={railed ? t.openSidebar : t.closeSidebar}
          aria-expanded={!railed}
          aria-controls="sidebar"
          title={railed ? t.openSidebar : t.closeSidebar}
          className={`absolute top-5 z-50 flex h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-ink-soft shadow-md transition-all duration-300 hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent ${
            railed ? "left-[68px]" : "left-[244px]"
          }`}
        >
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className={railed ? "" : "rotate-180"}
          >
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-line px-3 sm:px-4">
          {!leftOpen && (
            <button
              type="button"
              onClick={openLeft}
              aria-label={t.openMenu}
              aria-expanded={false}
              aria-controls="sidebar"
              className="flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Icon.Menu size={16} />
              <span className="hidden sm:inline">{t.menu}</span>
            </button>
          )}

          <div className="min-w-0 flex-1" />

          <button
            type="button"
            onClick={toggleLang}
            title={t.switchLang}
            aria-label={t.switchLang}
            className="flex items-center gap-1 rounded-md border border-transparent p-2 text-ink-soft transition-colors hover:border-line hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            <Icon.Globe />
            <span className="w-4 text-center text-[11px] font-bold tabular-nums">
              {lang}
            </span>
          </button>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? t.toLight : t.toDark}
            title={theme === "dark" ? t.toLight : t.toDark}
            className="rounded-md border border-transparent p-2 text-ink-soft transition-colors hover:border-line hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            {theme === "dark" ? <Icon.Sun /> : <Icon.Moon />}
          </button>

          <div className="mx-1 hidden h-5 w-px bg-line sm:block" />

          {!rightOpen && (
            <button
              type="button"
              onClick={openRight}
              aria-label={t.tracePanel}
              aria-expanded={false}
              aria-controls="trace"
              className="flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Icon.Panel size={16} />
              <span className="hidden sm:inline">{t.tracePanel}</span>
              {chunks.length > 0 && (
                <span className="rounded-full bg-cite-soft px-1.5 text-[10px] font-semibold text-cite tabular-nums">
                  {chunks.length}
                </span>
              )}
            </button>
          )}
        </header>

        {(waking || offline) && (
          <div
            role="status"
            className={`shrink-0 px-4 py-2 text-center text-xs ${
              offline
                ? "bg-danger-soft text-danger"
                : "animate-pulse-soft bg-warn-soft text-warn"
            }`}
          >
            {offline ? (
              <>
                {t.offline}{" "}
                <code className="font-mono">localhost:8000</code>
              </>
            ) : (
              t.waking
            )}
          </div>
        )}

        <main className="flex min-h-0 flex-1 flex-col">
          {nav === "chat" && (
            <Chat
              hasDocuments={ready.length > 0}
              turns={turns}
              onTurnsChange={setTurns}
              onRetrieval={setChunks}
              onAttach={goToUpload}
            />
          )}
          {nav === "knowledge" && (
            <div className="min-h-0 flex-1 overflow-y-auto">
              {knowledgePanel}
            </div>
          )}
          {nav === "about" && (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <AboutPage />
            </div>
          )}
          {nav === "how" && (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <HowItWorksPage />
            </div>
          )}
        </main>
      </div>

      {/* Right rail: retrieval evidence. */}
      {rightOpen && !isDesktop && (
        <div
          className="fixed inset-0 z-30 bg-ink/25 motion-safe:animate-fade-in"
          onClick={() => setRightOpen(false)}
          aria-hidden="true"
        />
      )}
      {rightOpen && (
        <aside
          id="trace"
          className={`z-40 flex w-[min(24rem,88vw)] shrink-0 flex-col border-l border-line bg-surface ${
            isDesktop
              ? "lg:w-80 xl:w-96"
              : "fixed inset-y-0 right-0 shadow-2xl motion-safe:animate-slide-in"
          }`}
          {...(!isDesktop && {
            role: "dialog",
            "aria-modal": true,
            "aria-label": "Jejak retrieval",
          })}
        >
          <div className="flex h-16 shrink-0 items-center justify-between gap-2 border-b border-line px-4">
            <h2 className="text-[13px] font-bold tracking-wider uppercase">
              {t.traceTitle}
            </h2>
            <button
              type="button"
              onClick={() => setRightOpen(false)}
              aria-label={t.traceClose}
              className="flex items-center gap-1 rounded p-1 text-xs font-medium text-ink-soft transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Icon.Close />
              
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {chunks.length > 0 ? (
              <RetrievalTrace chunks={chunks} />
            ) : (
              <p className="text-[11px] leading-relaxed text-ink-soft">
{t.traceEmpty}
              </p>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
