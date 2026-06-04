"use client";

import { useEffect, useState } from "react";

const GREETINGS: { text: string; lang: string }[] = [
  { text: "నమస్కారం", lang: "Telugu" },
  { text: "नमस्ते", lang: "Hindi" },
  { text: "வணக்கம்", lang: "Tamil" },
  { text: "ನಮಸ್ಕಾರ", lang: "Kannada" },
  { text: "നമസ്കാരം", lang: "Malayalam" },
  { text: "নমস্কার", lang: "Bengali" },
  { text: "नमस्कार", lang: "Marathi" },
  { text: "નમસ્તે", lang: "Gujarati" },
  { text: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", lang: "Punjabi" },
  { text: "ନମସ୍କାର", lang: "Odia" },
];

export function Hero() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((v) => (v + 1) % GREETINGS.length), 2200);
    return () => clearInterval(id);
  }, []);
  const g = GREETINGS[i];

  return (
    <div className="flex h-full min-h-[360px] flex-col items-start justify-center gap-3 p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
        ready when you are
      </div>
      <div className="relative h-[64px]">
        <div
          key={i}
          className="font-indic text-5xl font-semibold leading-none"
          style={{ animation: "greet-fade 2.2s ease-in-out" }}
        >
          {g.text}
        </div>
      </div>
      <div className="text-xs text-slate-400">
        Just typed in <span className="text-slate-200">{g.lang}</span>. Type back in any
        of the 10 supported languages and RUHI will reply in the same one.
      </div>
    </div>
  );
}
