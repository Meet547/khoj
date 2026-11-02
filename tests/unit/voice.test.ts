import { it, expect } from 'vitest';
import { amplitude, shouldStop } from '@/features/voice/silence';
it('stops at the provider-safe 28-second limit, even with ongoing speech', () => {
  expect(shouldStop(0, 28000, 28000)).toBe(true);
  expect(shouldStop(0, 27000, 27000)).toBe(false);
});
it('stops after 1.5 seconds of silence only after the initial grace period', () => {
  expect(shouldStop(0, 500, 1800)).toBe(false);
  expect(shouldStop(0, 1500, 3100)).toBe(true);
});
it('measures actual microphone amplitude', () => {
  expect(amplitude(new Uint8Array([128, 128, 128]))).toBe(0);
  expect(amplitude(new Uint8Array([0, 255]))).toBeGreaterThan(0.9);
});
