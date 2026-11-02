'use client';
import { useEffect, useRef, useState } from 'react';
import { amplitude, shouldStop, MAX_CLIP_MS } from './silence';
import type { RecorderError } from './types';
export function useRecorder(onClip: (clip: Blob) => Promise<void>) {
  const [state, setState] = useState<'idle' | 'listening' | 'processing' | 'error'>('idle');
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<RecorderError | null>(null);
  const [recorded, setRecorded] = useState(false);
  const active = useRef(true),
    recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    context = useRef<AudioContext | null>(null),
    frame = useRef(0),
    timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined),
    latest = useRef(onClip);
  useEffect(() => {
    latest.current = onClip;
  }, [onClip]);
  function cleanup() {
    clearTimeout(timer.current);
    cancelAnimationFrame(frame.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    if (context.current?.state !== 'closed') void context.current?.close();
    context.current = null;
    if (active.current) setLevel(0);
  }
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      if (recorder.current?.state === 'recording') recorder.current.stop();
      clearTimeout(timer.current);
      cancelAnimationFrame(frame.current);
      stream.current?.getTracks().forEach((t) => t.stop());
      if (context.current?.state !== 'closed') void context.current?.close();
    };
  }, []);
  async function start() {
    if (state === 'listening') {
      recorder.current?.stop();
      return;
    }
    setError(null);
    try {
      if (new URLSearchParams(location.search).get('mock') === 'micdenied')
        throw new DOMException('Microphone denied', 'NotAllowedError');
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined')
        throw new Error('Unavailable');
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!active.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const ctx = new AudioContext();
      context.current = ctx;
      await ctx.resume();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(media).connect(analyser);
      const data = new Uint8Array(analyser.fftSize);
      const rec = new MediaRecorder(media);
      recorder.current = rec;
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      rec.onstop = async () => {
        cleanup();
        if (!active.current) return;
        setState('processing');
        try {
          await latest.current(new Blob(chunks, { type: rec.mimeType }));
          if (active.current) {
            setState('idle');
            setRecorded(true);
          }
        } catch (e) {
          if (active.current) {
            setError({
              code: 'processing',
              message: e instanceof Error ? e.message : 'Please try again.',
            });
            setState('error');
          }
        }
      };
      rec.start();
      setState('listening');
      timer.current = setTimeout(() => {
        if (rec.state === 'recording') rec.stop();
      }, MAX_CLIP_MS);
      const started = performance.now();
      let lastSound = started,
        smoothed = 0;
      const tick = () => {
        if (rec.state !== 'recording') return;
        analyser.getByteTimeDomainData(data);
        const rms = amplitude(data),
          now = performance.now();
        smoothed = 0.75 * smoothed + 0.25 * Math.min(1, rms * 8);
        setLevel(smoothed);
        if (rms > 0.018) lastSound = now;
        if (shouldStop(started, lastSound, now)) {
          rec.stop();
          return;
        }
        frame.current = requestAnimationFrame(tick);
      };
      tick();
    } catch (e) {
      cleanup();
      if (active.current) {
        setError({
          code:
            e instanceof DOMException && e.name === 'NotAllowedError' ? 'denied' : 'unavailable',
          message: '',
        });
        setState('error');
      }
    }
  }
  return {
    state,
    level,
    error,
    recorded,
    start,
    stop: () => recorder.current?.state === 'recording' && recorder.current.stop(),
  };
}
