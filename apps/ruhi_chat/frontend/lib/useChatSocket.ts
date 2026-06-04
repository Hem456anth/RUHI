"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Server -> client frames, mirroring apps/ruhi_chat/backend/main.py.
export type ChatTurn = {
  event: "turn";
  detected_language: string;
  user_text_native: string;
  user_text_en: string;
  reply_en: string;
  reply_native: string;
  reply_audio_b64: string | null;
  tool_calls: string[];
  input_mode: "text" | "voice";
};

export type ChatError = { event: "error"; detail: string; code?: string };
export type ChatResetOk = { event: "reset_ok" };
export type ChatServerFrame = ChatTurn | ChatError | ChatResetOk;

export type ChatStatus = "idle" | "connecting" | "open" | "closed" | "error";

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  language?: string;
  tool_calls?: string[];
  audio?: string | null; // base64 wav
};

interface UseChatSocketOptions {
  url?: string;
  onError?: (detail: string) => void;
}

const DEFAULT_WS =
  (typeof process !== "undefined" &&
    (process.env.NEXT_PUBLIC_RUHI_WS as string | undefined)) ||
  "ws://localhost:8001";

export function useChatSocket(opts: UseChatSocketOptions = {}) {
  const url = opts.url ?? `${DEFAULT_WS}/chat/ws`;

  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);

  // Keep the latest onError in a ref so the callback identity doesn't
  // force the socket to reconnect every parent re-render.
  const onErrorRef = useRef(opts.onError);
  useEffect(() => {
    onErrorRef.current = opts.onError;
  }, [opts.onError]);

  // Track whether the consumer asked us to disconnect (StrictMode cleanup
  // shouldn't trigger reconnection logic).
  const intentionalCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return; // SSR no-op
    const existing = wsRef.current;
    if (existing && existing.readyState <= WebSocket.OPEN) {
      return; // already connecting or open
    }

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;
    intentionalCloseRef.current = false;

    ws.onopen = () => setStatus("open");

    ws.onclose = () => {
      // Only flip to "closed" if this socket is still the active one
      // (avoids races where a new connect already replaced it).
      if (wsRef.current === ws) {
        setStatus(intentionalCloseRef.current ? "closed" : "closed");
        setBusy(false);
      }
    };

    ws.onerror = () => {
      if (wsRef.current === ws) setStatus("error");
    };

    ws.onmessage = (e) => {
      let frame: ChatServerFrame;
      try {
        frame = JSON.parse(e.data);
      } catch {
        return;
      }
      if (frame.event === "turn") {
        setMessages((m) => [
          ...m,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: frame.reply_native,
            language: frame.detected_language,
            tool_calls: frame.tool_calls,
            audio: frame.reply_audio_b64,
          },
        ]);
        setBusy(false);
      } else if (frame.event === "error") {
        setBusy(false);
        onErrorRef.current?.(frame.detail);
        setMessages((m) => [
          ...m,
          { id: crypto.randomUUID(), role: "system", text: `Error: ${frame.detail}` },
        ]);
      } else if (frame.event === "reset_ok") {
        setMessages([]);
        setBusy(false);
      }
    };
  }, [url]); // ← only re-creates if the URL itself changes

  useEffect(() => {
    connect();
    return () => {
      intentionalCloseRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const sendText = useCallback(
    (
      text: string,
      options: { wantAudio?: boolean; hintLanguage?: string; speaker?: string } = {},
    ) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        text,
        language: options.hintLanguage,
      };
      setMessages((m) => [...m, userMsg]);
      setBusy(true);
      ws.send(
        JSON.stringify({
          type: "text",
          text,
          want_audio: options.wantAudio ?? false,
          hint_language: options.hintLanguage,
          speaker: options.speaker,
        }),
      );
      return true;
    },
    [],
  );

  const sendAudio = useCallback(
    (audioB64: string, options: { wantAudio?: boolean; hintLanguage?: string } = {}) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: "user", text: "🎙️ (voice)" },
      ]);
      setBusy(true);
      ws.send(
        JSON.stringify({
          type: "audio",
          audio_b64: audioB64,
          want_audio: options.wantAudio ?? true,
          hint_language: options.hintLanguage,
        }),
      );
      return true;
    },
    [],
  );

  const reset = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "reset" }));
  }, []);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    connect();
  }, [connect]);

  return { status, messages, busy, sendText, sendAudio, reset, reconnect };
}
