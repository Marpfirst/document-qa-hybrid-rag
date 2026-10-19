const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const Icon = {
  Plus: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  Chat: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  Book: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
  Info: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  ),
  Help: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01" />
    </svg>
  ),
  Panel: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M15 3v18" />
    </svg>
  ),
  Menu: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="M3 6h18M3 12h18M3 18h18" />
    </svg>
  ),
  Close: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  ),
  Send: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </svg>
  ),
  Paperclip: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  ),
  Mic: (p: { size?: number; active?: boolean }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
      {p.active && (
        <circle cx="19.5" cy="4.5" r="2.5" fill="currentColor" stroke="none" />
      )}
    </svg>
  ),
  Sun: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  ),
  Moon: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  ),
  Trash: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 14} height={p.size ?? 14}>
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
    </svg>
  ),
  Globe: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  ),
  Bot: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4M8 16h.01M16 16h.01" />
    </svg>
  ),
};
