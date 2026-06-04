"use client";

import { useEffect, useRef, useState } from "react";

import { Brand } from "@/components/Brand";
import { Composer } from "@/components/Composer";
import { Hero } from "@/components/Hero";
import { LangSwitcher } from "@/components/LangSwitcher";
import { MessageBubble } from "@/components/MessageBubble";
import { StatusDot } from "@/components/StatusDot";
import { SuggestionChips } from "@/components/SuggestionChips";
import { LANGUAGES, type LangCode } from "@/lib/languages";
import { useChatSocket } from "@/lib/useChatSocket";

export default function ChatPage() {
  const [hintLanguage, setHintLanguage] = useState<LangCode>("auto");
  const [wantAudio, setWantAudio] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { status, messages, busy, sendText, sendAudio, reset, reconnect } =
    useChatSocket({
      onError: (detail) => console.warn("RUHI error:", detail),
    });

  const scrollerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, busy]);

  const handleSend = (text: string, langOverride?: string) => {
    sendText(text, {
      wantAudio,
      hintLanguage:
        (langOverride as LangCode | undefined) ??
        (hintLanguage === "auto" ? undefined : hintLanguage),
    });
  };

  const handleVoice = (audioB64: string) => {
    sendAudio(audioB64, {
      wantAudio: true,
      hintLanguage: hintLanguage === "auto" ? undefined : hintLanguage,
    });
  };

  return (
    <div className="bg-grid min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px]">
        {/* ────────── Sidebar ────────── */}
        <aside
          className={[
            "fixed inset-y-0 left-0 z-30 w-72 shrink-0 border-r border-line bg-ink-0 px-5 py-5",
            "transition-transform md:static md:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full",
          ].join(" ")}
        >
          <div className="flex items-center justify-between">
            <Brand />
            <button
              type="button"
              className="md:hidden text-slate-500"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
            >
              ✕
            </button>
          </div>

          <div className="my-5 hairline" />

          <div className="space-y-5">
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                Language
              </div>
              <LangSwitcher value={hintLanguage} onChange={setHintLanguage} />
              <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
                Leave on{" "}
                <span className="text-slate-300">Auto</span> to let Sarvam detect.
                Setting a language explicitly skips one API call per turn.
              </p>
            </div>

            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                Supported
              </div>
              <ul className="grid grid-cols-2 gap-y-1 text-[12px] text-slate-300">
                {LANGUAGES.filter((l) => l.code !== "auto" && l.code !== "en").map((l) => (
                  <li key={l.code} className="flex items-baseline gap-1.5">
                    <span className="font-indic">{l.native}</span>
                    <span className="text-[9px] uppercase text-slate-500">{l.code}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                Pipeline
              </div>
              <ol className="space-y-1.5 text-[11px] text-slate-400">
                {[
                  ["LID", "Sarvam · text-lid"],
                  ["ASR", "Saarika v2.5"],
                  ["NMT", "Mayura v1"],
                  ["LLM", "Gemini 2.5 Flash"],
                  ["TTS", "Bulbul v3"],
                ].map(([k, v]) => (
                  <li key={k} className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-[10px] text-slate-500">{k}</span>
                    <span className="truncate text-right">{v}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          <div className="absolute inset-x-5 bottom-5 flex items-center justify-between text-[10px] text-slate-500">
            <StatusDot status={status} />
            <span>v0.2.0</span>
          </div>
        </aside>

        {/* ────────── Main ────────── */}
        <main className="flex min-h-screen flex-1 flex-col">
          {/* Top bar — mobile sidebar toggle + connection + actions */}
          <header className="flex items-center justify-between border-b border-line px-4 py-3 md:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open menu"
                className="md:hidden grid h-8 w-8 place-items-center rounded-md border border-line"
              >
                <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M4 6h12M4 10h12M4 14h12" />
                </svg>
              </button>
              <div className="hidden md:block">
                <StatusDot status={status} />
              </div>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              {(status === "closed" || status === "error") && (
                <button
                  onClick={reconnect}
                  className="rounded-md border border-line bg-ink-2 px-2.5 py-1 text-slate-200 hover:border-line-strong"
                >
                  Reconnect
                </button>
              )}
              <button
                onClick={reset}
                disabled={messages.length === 0}
                className="rounded-md border border-line bg-ink-2 px-2.5 py-1 text-slate-300 hover:border-line-strong disabled:opacity-40"
                title="Clear conversation"
              >
                Reset
              </button>
            </div>
          </header>

          {/* Message column */}
          <section
            ref={scrollerRef}
            className="relative flex-1 overflow-y-auto px-4 md:px-8 py-4"
          >
            {messages.length === 0 ? (
              <div className="mx-auto max-w-2xl">
                <Hero />
                <div className="px-1 pt-2">
                  <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                    Try one
                  </div>
                  <SuggestionChips
                    onPick={(text, lang) => {
                      setHintLanguage(lang as LangCode);
                      handleSend(text, lang);
                    }}
                  />
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl pb-2">
                {messages.map((m, idx) => {
                  // Pair each assistant reply with the prior user message's
                  // english pivot, if any — gives "show English" useful content.
                  const englishOriginal =
                    m.role === "assistant"
                      ? undefined
                      : undefined; /* placeholder for a future enhancement */
                  return (
                    <MessageBubble
                      key={m.id + idx}
                      message={m}
                      englishOriginal={englishOriginal}
                    />
                  );
                })}
                {busy && (
                  <div className="my-2 ml-9 flex items-center gap-2 text-[12px] text-slate-400">
                    <span className="dot-pulse">
                      <span /><span /><span />
                    </span>
                    <span>
                      RUHI is{" "}
                      <span className="text-slate-200">translating, thinking, answering</span>
                      …
                    </span>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Composer pinned to bottom */}
          <div className="border-t border-line px-4 py-3 md:px-8">
            <div className="mx-auto max-w-3xl">
              <Composer
                busy={busy || status !== "open"}
                wantAudio={wantAudio}
                onWantAudioChange={setWantAudio}
                onSend={handleSend}
                onVoice={handleVoice}
              />
              <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-500">
                <span>
                  Backend ·{" "}
                  <span className="text-slate-300">
                    {process.env.NEXT_PUBLIC_RUHI_API}
                  </span>
                </span>
                <span>
                  Cached calls cost <span className="text-slate-300">0 credits</span>
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
