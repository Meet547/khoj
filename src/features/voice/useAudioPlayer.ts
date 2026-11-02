'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
export function useAudioPlayer(text: string, lang: string, url?: string) {
  const [speaking, setSpeaking] = useState(false),
    [muted, setMuted] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);
  const stop = useCallback(() => {
    audio.current?.pause();
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    setSpeaking(false);
  }, []);
  const play = useCallback(() => {
    if (muted) return;
    stop();
    if (url) {
      const a = new Audio(url);
      audio.current = a;
      a.onended = a.onerror = () => setSpeaking(false);
      setSpeaking(true);
      void a.play().catch(() => setSpeaking(false));
    } else if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang + '-IN';
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = utterance.onerror = () => setSpeaking(false);
      speechSynthesis.speak(utterance);
    }
  }, [text, lang, url, muted, stop]);
  useEffect(() => {
    if (text) play();
    return () => {
      audio.current?.pause();
      if ('speechSynthesis' in window) speechSynthesis.cancel();
    };
  }, [text, play]);
  return {
    speaking,
    muted,
    play,
    stop,
    toggleMute: () => {
      stop();
      setMuted(!muted);
    },
  };
}
