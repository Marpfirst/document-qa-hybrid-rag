"use client";

import { Icon } from "@/components/Icons";
import { useLang } from "@/lib/i18n";
import type { Conversation } from "@/lib/conversations";

export type NavKey = "chat" | "knowledge" | "about" | "how";

const NAV: { key: NavKey; icon: React.ReactNode }[] = [
  { key: "chat", icon: <Icon.Chat /> },
  { key: "knowledge", icon: <Icon.Book /> },
  { key: "about", icon: <Icon.Info /> },
  { key: "how", icon: <Icon.Help /> },
];

const NAV_LABEL = {
  chat: "navChat",
  knowledge: "navKnowledge",
  about: "navAbout",
  how: "navHow",
} as const;

interface Props {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  conversations: Conversation[];
  currentId: string | null;
  onNewChat: () => void;
  onOpenConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  readyCount: number;
  /** Rail mode: icons only. Desktop-only; the mobile drawer is always full. */
  collapsed?: boolean;
  onClose?: () => void;
}

export default function Sidebar({
  active,
  onNavigate,
  conversations,
  currentId,
  onNewChat,
  onOpenConversation,
  onDeleteConversation,
  readyCount,
  collapsed = false,
  onClose,
}: Props) {
  const { t } = useLang();

  // Labels collapse by animating width to zero instead of unmounting, so the
  // text slides away with the rail rather than popping out of existence.
  const label = (extra = "") =>
    `overflow-hidden whitespace-nowrap transition-all duration-300 ${
      collapsed ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"
    } ${extra}`;

  return (
    <div className="relative flex h-full flex-col bg-surface">
      <div
        className={`flex h-16 shrink-0 items-center border-b border-line transition-all duration-300 ${
          collapsed ? "justify-center px-0" : "gap-3 px-4"
        }`}
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-white">
          <Icon.Bot />
        </span>
        <div className={label("min-w-0 flex-1")}>
          <p className="truncate text-sm font-bold tracking-tight">
            {t.brand}
          </p>
          <p className="truncate text-[10px] font-medium text-ink-soft">
            {t.brandSub}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label={t.closeMenu}
            className="rounded p-1 text-ink-soft hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
          >
            <Icon.Close />
          </button>
        )}
      </div>

      <div className={collapsed ? "px-2 py-4" : "p-4"}>
        <button
          type="button"
          onClick={onNewChat}
          title={collapsed ? t.newChat : undefined}
          aria-label={collapsed ? t.newChat : undefined}
          className={`flex w-full items-center justify-center rounded-lg bg-accent py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 ${
            collapsed ? "px-0" : "gap-2 px-4"
          }`}
        >
          <Icon.Plus />
          <span className={label()}>{t.newChat}</span>
        </button>
      </div>

      <nav
        className={collapsed ? "space-y-1 px-2" : "space-y-1 px-3"}
        aria-label={t.navAria}
      >
        {NAV.map((item) => {
          const itemLabel = t[NAV_LABEL[item.key]];
          const isActive = active === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onNavigate(item.key)}
              aria-current={isActive ? "page" : undefined}
              title={collapsed ? itemLabel : undefined}
              aria-label={collapsed ? itemLabel : undefined}
              className={`flex w-full items-center rounded-md py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-accent ${
                collapsed ? "justify-center px-0" : "gap-3 px-3"
              } ${
                isActive
                  ? "bg-accent-soft text-accent"
                  : "text-ink-soft hover:bg-accent-soft/60 hover:text-ink"
              }`}
            >
              <span className={isActive ? "text-accent" : "text-ink-soft"}>
                {item.icon}
              </span>
              <span className={label("flex-1 text-left")}>{itemLabel}</span>
              {item.key === "knowledge" && readyCount > 0 && !collapsed && (
                <span className="rounded-full bg-cite-soft px-1.5 text-[10px] font-semibold text-cite tabular-nums">
                  {readyCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* The history list is meaningless as icons, so the rail drops it. */}
      {!collapsed && (
        <div className="mt-6 flex min-h-0 flex-1 flex-col">
          <h2 className="px-4 pb-2 text-[10px] font-semibold tracking-wider uppercase text-ink-soft">
            {t.recent}
          </h2>
          <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
            {conversations.length === 0 ? (
              <p className="px-1 text-[11px] leading-relaxed text-ink-soft">
                {t.recentEmpty}
              </p>
            ) : (
              <ul className="space-y-0.5">
                {conversations.map((c) => {
                  const isCurrent = c.id === currentId;
                  return (
                    <li key={c.id} className="group relative">
                      <button
                        type="button"
                        onClick={() => onOpenConversation(c.id)}
                        className={`w-full truncate rounded-md py-2 pr-8 pl-3 text-left text-[13px] transition-colors focus-visible:outline-2 focus-visible:outline-accent ${
                          isCurrent
                            ? "bg-accent-soft font-medium text-accent"
                            : "text-ink-soft hover:bg-accent-soft/60 hover:text-ink"
                        }`}
                      >
                        {c.title}
                      </button>
                      <button
                        type="button"
                        onClick={() => onDeleteConversation(c.id)}
                        aria-label={`Hapus percakapan ${c.title}`}
                        className="absolute top-1/2 right-1 -translate-y-1/2 rounded p-1.5 text-ink-soft opacity-0 transition-opacity group-hover:opacity-100 hover:text-danger focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-accent"
                      >
                        <Icon.Trash />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {collapsed && <div className="flex-1" />}

      {!collapsed && (
        <div className="shrink-0 border-t border-line p-4">
          <div className="flex gap-2.5 rounded-lg bg-accent-soft p-3">
            <span className="mt-0.5 shrink-0 text-accent">
              <Icon.Info size={16} />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-accent">{t.demoTitle}</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-ink-soft">
                {t.demoBody}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
