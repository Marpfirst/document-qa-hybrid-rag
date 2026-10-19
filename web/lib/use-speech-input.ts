"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// The Web Speech API is not in TypeScript's DOM lib, and it ships prefixed in
// Chrome. Declaring only the surface used here keeps the shim honest.
interface SpeechRecognitionAlternative {
  transcript: string;
}
interface SpeechRecognitionResult {
  readonly length: number;
  isFinal: boolean;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionEventLike extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getConstructor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const ERROR_MESSAGE: Record<string, string> = {
  "not-allowed": "Izin mikrofon ditolak. Aktifkan lewat pengaturan situs.",
  "service-not-allowed": "Izin mikrofon ditolak oleh browser.",
  "no-speech": "Tidak ada suara terdeteksi. Coba lagi.",
  "audio-capture": "Mikrofon tidak ditemukan.",
  network: "Pengenalan suara butuh koneksi internet.",
};

interface Options {
  /** Called with the full transcript each time it grows. */
  onTranscript: (text: string) => void;
  lang?: string;
}

/**
 * Dictation via the browser's own speech recognition.
 *
 * `supported` is false on Firefox and older Safari; callers must hide the
 * control rather than render one that does nothing when clicked.
 *
 * Note for users: in Chrome this streams audio to Google for transcription,
 * so it is not an on-device feature.
 */
export function useSpeechInput({ onTranscript, lang = "id-ID" }: Options) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onTranscriptRef = useRef(onTranscript);

  // Keep the latest callback without re-creating the recognizer mid-session.
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    const Ctor = getConstructor();
    if (!Ctor) return;
    setSupported(true);

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let text = "";
      for (let i = 0; i < event.results.length; i += 1) {
        text += event.results[i][0].transcript;
      }
      onTranscriptRef.current(text.trim());
    };
    recognition.onerror = (event) => {
      setError(ERROR_MESSAGE[event.error] ?? "Pengenalan suara gagal.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const toggle = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    if (listening) {
      recognition.stop();
      setListening(false);
      return;
    }
    setError(null);
    try {
      recognition.start();
      setListening(true);
    } catch {
      // start() throws if called while already running; treat as a no-op.
      setListening(true);
    }
  }, [listening]);

  return { supported, listening, error, toggle };
}
