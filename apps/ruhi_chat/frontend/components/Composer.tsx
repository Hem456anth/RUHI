"use client";

import { useRef, useState } from "react";

interface Props {
  busy: boolean;
  wantAudio: boolean;
  onWantAudioChange: (v: boolean) => void;
  onSend: (text: string) => void;
  onVoice: (audioB64: string) => void;
}

export function Composer({ busy, wantAudio, onWantAudioChange, onSend, onVoice }: Props) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordSec, setRecordSec] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  };

  const startTimer = () => {
    setRecordSec(0);
    timerRef.current = setInterval(() => setRecordSec((s) => s + 1), 1000);
  };
  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const toggleRecord = async () => {
    if (recording) {
      recorderRef.current?.stop();
      setRecording(false);
      stopTimer();
      return;
    }
    if (typeof navigator === "undefined" || !navigator.mediaDevices) {
      alert("Microphone unavailable in this browser/context.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => chunksRef.current.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const buf = await blob.arrayBuffer();
        const b64 = btoa(
          new Uint8Array(buf).reduce((acc, b) => acc + String.fromCharCode(b), ""),
        );
        onVoice(b64);
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
      startTimer();
    } catch (err) {
      const name = err instanceof Error ? err.name : "Error";
      const msg = err instanceof Error ? err.message : String(err);
      alert(
        `Microphone error: ${name}\n${msg}\n\nFix: lock icon → Microphone → Allow, then refresh.`,
      );
    }
  };

  const disabledSend = busy || !text.trim();

  return (
    <div className="panel-strong rounded-xl">
      {/* Row 1 — textarea + action buttons. Single line, no wrapping. */}
      <div className="flex items-stretch gap-2 p-2">
        <textarea
          className="font-indic min-h-[44px] flex-1 resize-none rounded-md bg-transparent px-3 py-2.5 text-[15px] text-slate-100 placeholder:text-slate-500 focus:outline-none"
          rows={1}
          value={text}
          placeholder="Ask in any Indian language · Telugu · Hindi · Tamil…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          disabled={busy}
        />

        {/* Mic — square, neutral chrome */}
        <button
          type="button"
          onClick={toggleRecord}
          disabled={busy && !recording}
          className={[
            "grid h-11 w-11 shrink-0 place-items-center rounded-md transition",
            recording
              ? "recording bg-rose-500/90 text-white"
              : "border border-line bg-ink-2 text-slate-200 hover:border-line-strong hover:bg-ink-3 disabled:opacity-40",
          ].join(" ")}
          title={recording ? `Recording ${recordSec}s — click to stop` : "Record voice"}
          aria-label={recording ? "Stop recording" : "Record voice"}
        >
          {recording ? (
            <span className="block h-3 w-3 rounded-sm bg-white" />
          ) : (
            <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="9" y="3" width="6" height="12" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0" />
              <path d="M12 18v3" />
            </svg>
          )}
        </button>

        {/* Send — wider, primary accent, single-line label */}
        <button
          type="button"
          onClick={submit}
          disabled={disabledSend}
          className={[
            "inline-flex h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-md px-4 text-sm font-medium transition",
            disabledSend
              ? "border border-line bg-ink-2 text-slate-500"
              : "border border-accent/40 bg-accent-soft text-accent hover:bg-accent/20 hover:text-white",
          ].join(" ")}
          aria-label="Send message"
        >
          {busy ? (
            <span className="dot-pulse">
              <span /><span /><span />
            </span>
          ) : (
            <>
              <span>Send</span>
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M2 8h11M9 4l4 4-4 4" />
              </svg>
            </>
          )}
        </button>
      </div>

      {/* Row 2 — sub-bar, hairline-separated. Single tight line. */}
      <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-1.5 text-[11px] text-slate-500">
        <label className="flex cursor-pointer items-center gap-2 select-none">
          <input
            type="checkbox"
            className="h-3 w-3 accent-accent"
            checked={wantAudio}
            onChange={(e) => onWantAudioChange(e.target.checked)}
          />
          <span>Voice reply <span className="text-slate-600">· Bulbul TTS · costs credits</span></span>
        </label>
        <div className="flex items-center gap-3">
          {recording && (
            <span className="inline-flex items-center gap-1 text-rose-300">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-rose-400" />
              recording · {recordSec}s
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <span className="kbd">↵</span> send
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="kbd">Shift</span>
            <span className="kbd">↵</span> newline
          </span>
        </div>
      </div>
    </div>
  );
}
