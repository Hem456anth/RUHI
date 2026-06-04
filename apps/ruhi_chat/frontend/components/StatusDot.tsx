import type { ChatStatus } from "@/lib/useChatSocket";

const STATE: Record<ChatStatus, { dot: string; ring: string; label: string }> = {
  idle:       { dot: "bg-slate-500", ring: "ring-slate-500/30", label: "idle" },
  connecting: { dot: "bg-amber-400 animate-pulse", ring: "ring-amber-400/30", label: "connecting" },
  open:       { dot: "bg-emerald-400", ring: "ring-emerald-400/30", label: "live" },
  closed:     { dot: "bg-slate-500", ring: "ring-slate-500/30", label: "offline" },
  error:      { dot: "bg-rose-500", ring: "ring-rose-500/30", label: "error" },
};

export function StatusDot({ status }: { status: ChatStatus }) {
  const s = STATE[status];
  return (
    <span className="inline-flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400">
      <span className={`relative inline-flex h-2 w-2 rounded-full ${s.dot} ring-4 ${s.ring}`} />
      {s.label}
    </span>
  );
}
