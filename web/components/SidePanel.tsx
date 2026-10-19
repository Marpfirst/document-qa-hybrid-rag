"use client";

import { useEffect, useRef } from "react";
import { useIsDesktop } from "@/lib/use-media-query";

interface Props {
  side: "left" | "right";
  open: boolean;
  onClose: () => void;
  title: string;
  /** Rendered next to the title — status counts, hints. */
  meta?: React.ReactNode;
  children: React.ReactNode;
}

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

/**
 * A rail that collapses inline on desktop and becomes a modal drawer on mobile.
 *
 * Both modes unmount their contents when closed rather than hiding them with
 * width or opacity. A visually hidden panel that stays in the DOM is still
 * reachable by Tab and still announced by screen readers, so the keyboard
 * focus disappears into a panel the user cannot see.
 */
export default function SidePanel({
  side,
  open,
  onClose,
  title,
  meta,
  children,
}: Props) {
  const isDesktop = useIsDesktop();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const isDrawer = open && !isDesktop;

  // Drawer only: Escape closes, focus moves in, background scroll locks.
  useEffect(() => {
    if (!isDrawer) return;

    closeRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      // Keep Tab inside the drawer while it covers the page.
      const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea, select, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isDrawer, onClose]);

  if (!open) return null;

  const header = (
    <div className="flex items-baseline justify-between gap-2 border-b border-line px-4 py-3">
      <div className="min-w-0">
        <h2 className="text-xs font-semibold tracking-wider uppercase text-ink-soft">
          {title}
        </h2>
        {meta && <div className="mt-0.5 text-[11px] text-ink-soft">{meta}</div>}
      </div>
      <button
        ref={closeRef}
        type="button"
        onClick={onClose}
        aria-label={`Tutup panel ${title}`}
        className="-mr-1 shrink-0 rounded p-1 text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
      >
        <CloseIcon />
      </button>
    </div>
  );

  if (isDrawer) {
    return (
      <>
        <div
          className="fixed inset-0 z-30 bg-ink/25 backdrop-blur-[1px] motion-safe:animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-label={title}
          className={`fixed inset-y-0 z-40 flex w-[min(20rem,85vw)] flex-col bg-surface shadow-2xl motion-safe:animate-slide-in ${
            side === "left" ? "left-0 border-r" : "right-0 border-l"
          } border-line`}
        >
          {header}
          <div className="min-h-0 flex-1 overflow-y-auto p-4">{children}</div>
        </div>
      </>
    );
  }

  return (
    <aside
      className={`hidden min-h-0 w-72 shrink-0 flex-col bg-surface lg:flex xl:w-80 ${
        side === "left" ? "border-r" : "border-l"
      } border-line`}
    >
      {header}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">{children}</div>
    </aside>
  );
}
