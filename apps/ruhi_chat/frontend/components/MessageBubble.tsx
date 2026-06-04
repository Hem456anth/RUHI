"use client";

import { useState } from "react";

import type { Message } from "@/lib/useChatSocket";

interface Props {
  message: Message;
  englishOriginal?: string; // optional: the EN translation that flowed through the pipeline
}

export function MessageBubble({ message, englishOriginal }: Props) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const [showEn, setShowEn] = useState(false);

  if (isSystem) {
    return (
      <div className="my-2 flex items-center gap-2">
        <div className="h-px flex-1 bg-rose-500/20" />
        <span className="rounded-sm border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-rose-300">
          {message.text}
        </span>
        <div className="h-px flex-1 bg-rose-500/20" />
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} gap-2 my-2`}>
      {!isUser && (
        <div
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-ink-2 text-[11px] font-semibold text-accent"
          aria-hidden
        >
          R
        </div>
      )}
      <div className={`max-w-[78%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {/* Tool-call ticker, above the bubble */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-1 flex flex-wrap items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
            <span>used</span>
            {message.tool_calls.map((t, i) => (
              <span
                key={`${t}-${i}`}
                className="rounded-sm border border-accent/30 bg-accent-soft px-1.5 py-0.5 font-mono text-[10px] text-accent"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        <div
          className={[
            "px-3.5 py-2.5 text-[15px] leading-relaxed",
            isUser
              ? "bubble-user bg-accent-soft text-white border border-accent/30"
              : "bubble-assistant bg-ink-2 text-slate-100 border border-line",
          ].join(" ")}
        >
          <div className="font-indic whitespace-pre-wrap">{message.text}</div>

          {/* Reveal the English the agent actually saw */}
          {englishOriginal && englishOriginal !== message.text && (
            <div className="mt-2">
              <button
                type="button"
                onClick={() => setShowEn((v) => !v)}
                className="text-[10px] uppercase tracking-wider text-slate-400 hover:text-slate-200"
              >
                {showEn ? "hide English" : "show English"}
              </button>
              {showEn && (
                <div className="mt-1 border-l-2 border-line pl-2 text-[13px] text-slate-300">
                  {englishOriginal}
                </div>
              )}
            </div>
          )}

          {message.audio && (
            <audio
              controls
              className="mt-2 w-full"
              src={`data:audio/wav;base64,${message.audio}`}
            />
          )}
        </div>

        {/* Footnote — detected language only on assistant replies */}
        {!isUser && message.language && (
          <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
            {message.language}
          </div>
        )}
      </div>
      {isUser && (
        <div
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-ink-2 text-[11px] font-semibold text-slate-300"
          aria-hidden
        >
          U
        </div>
      )}
    </div>
  );
}
