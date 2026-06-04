"use client";

import { useEffect, useRef, useState } from "react";

import { LANGUAGES, type LangCode } from "@/lib/languages";

interface Props {
  value: LangCode;
  onChange: (code: LangCode) => void;
}

/**
 * Custom dropdown — native <select> on dark backgrounds renders inconsistently
 * across OSes, and we want to show each language in its own script.
 */
export function LangSwitcher({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const current = LANGUAGES.find((l) => l.code === value) ?? LANGUAGES[0];

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-md border border-line bg-ink-2 px-3 py-2 text-left text-sm hover:border-line-strong"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="flex items-baseline gap-2">
          <span className="font-indic">{current.native}</span>
          <span className="text-[10px] uppercase tracking-wider text-slate-500">
            {current.code}
          </span>
        </span>
        <svg viewBox="0 0 12 8" className="h-2.5 w-3 text-slate-400">
          <path d="M1 1l5 5 5-5" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 right-0 z-20 mt-1 max-h-72 overflow-y-auto rounded-md border border-line bg-ink-1 shadow-xl shadow-black/40"
        >
          {LANGUAGES.map((l) => {
            const selected = l.code === value;
            return (
              <button
                key={l.code}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  onChange(l.code);
                  setOpen(false);
                }}
                className={[
                  "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm",
                  selected
                    ? "bg-accent-soft text-white"
                    : "text-slate-200 hover:bg-white/5",
                ].join(" ")}
              >
                <span className="font-indic">{l.native}</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-500">
                  {l.label}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
