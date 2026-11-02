export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';
export interface RecorderError {
  code: 'denied' | 'unavailable' | 'processing';
  message: string;
}
