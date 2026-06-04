"use client";

interface Props {
  onPick: (text: string, lang: string) => void;
}

const SUGGESTIONS: { text: string; lang: string; hint: string; code: string }[] = [
  { text: "నాకు హైదరాబాద్ వాతావరణం చెప్పు", lang: "Telugu",  hint: "weather in Hyderabad", code: "te" },
  { text: "आज की मुख्य खबरें क्या हैं?",       lang: "Hindi",   hint: "top news today",       code: "hi" },
  { text: "சென்னையில் என்ன நிகழ்வுகள் உள்ளன?",  lang: "Tamil",   hint: "events in Chennai",    code: "ta" },
  { text: "How does the Sarvam pipeline work?",   lang: "English", hint: "ask in English",       code: "en" },
];

export function SuggestionChips({ onPick }: Props) {
  return (
    <div className="flex flex-wrap gap-2 px-1 pt-2">
      {SUGGESTIONS.map((s) => (
        <button
          key={s.code + s.hint}
          type="button"
          onClick={() => onPick(s.text, s.code)}
          className="group flex max-w-[280px] items-start gap-2 rounded-lg border border-line bg-ink-1 px-3 py-2 text-left hover:border-accent/60 hover:bg-ink-2"
        >
          <span className="mt-0.5 inline-flex h-5 min-w-[34px] items-center justify-center rounded-sm border border-line bg-ink-2 text-[10px] uppercase tracking-wider text-slate-400">
            {s.code}
          </span>
          <span className="min-w-0">
            <span className="font-indic block truncate text-[13px] text-slate-200 group-hover:text-white">
              {s.text}
            </span>
            <span className="block text-[11px] text-slate-500">{s.hint}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
