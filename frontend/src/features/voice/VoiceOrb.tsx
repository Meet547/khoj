'use client';
import { useEffect, type CSSProperties } from 'react';
import { Mic, Square, LoaderCircle, RotateCcw, Volume2, VolumeX } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useApp } from '@/components/providers';
import { useRecorder } from './useRecorder';
import { useAudioPlayer } from './useAudioPlayer';
export function VoiceOrb({
  question,
  onAudio,
  busy = false,
  replyAudioUrl,
}: {
  question: string;
  onAudio: (audio: Blob) => Promise<void>;
  busy?: boolean;
  replyAudioUrl?: string;
}) {
  const t = useTranslations();
  const { lang, setMode, toast } = useApp();
  const recorder = useRecorder(onAudio);
  const player = useAudioPlayer(question, lang, replyAudioUrl);
  const message = recorder.error?.message || t('voiceUnavailable');
  useEffect(() => {
    if (recorder.error) {
      toast(message);
      setMode('text');
    }
  }, [recorder.error, message, setMode, toast]);
  const visual = busy ? 'processing' : player.speaking ? 'speaking' : recorder.state;
  return (
    <div className="voice-container">
      <button
        type="button"
        className={`voice-orb ${visual}`}
        style={{ '--level': recorder.level } as CSSProperties}
        disabled={busy || recorder.state === 'processing'}
        onClick={() => {
          player.stop();
          void recorder.start();
        }}
        aria-label={visual === 'listening' ? t('listening') : t('tapSpeak')}
        aria-pressed={visual === 'listening'}
      >
        {visual === 'processing' ? (
          <LoaderCircle size={31} className="spinner" />
        ) : visual === 'listening' ? (
          <Square size={27} />
        ) : visual === 'error' ? (
          <RotateCcw size={30} />
        ) : (
          <Mic size={32} />
        )}
      </button>
      <p className="voice-label" aria-live="polite">
        {recorder.error
          ? message
          : t(
              visual === 'processing'
                ? 'processing'
                : visual === 'listening'
                  ? 'listening'
                  : recorder.recorded
                    ? 'keepTalking'
                    : 'tapSpeak',
            )}
      </p>
      <div className="voice-controls">
        <button type="button" onClick={player.play}>
          <Volume2 size={14} />
          {t('replay')}
        </button>
        <button type="button" onClick={player.toggleMute}>
          {player.muted ? <VolumeX size={14} /> : <Volume2 size={14} />}{' '}
          {t(player.muted ? 'unmute' : 'mute')}
        </button>
      </div>
    </div>
  );
}
