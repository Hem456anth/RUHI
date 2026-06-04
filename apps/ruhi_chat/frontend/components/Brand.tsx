export function Brand({ subtitle = true }: { subtitle?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="grid h-9 w-9 place-items-center rounded-lg border border-line-strong bg-ink-2 text-accent shadow-[inset_0_0_0_1px_rgba(56,189,248,0.18)]"
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M4 12c2-5 6-8 8-8s6 3 8 8c-2 5-6 8-8 8s-6-3-8-8Z" />
          <circle cx="12" cy="12" r="2.5" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-wide">
          RUHI <span className="text-accent">·</span> Chat
        </div>
        {subtitle && (
          <div className="text-[11px] text-slate-400">
            10 Indian languages · Sarvam pipeline
          </div>
        )}
      </div>
    </div>
  );
}
