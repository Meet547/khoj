export const MAX_CLIP_MS = 28000;
export function amplitude(samples: Uint8Array): number {
  let sum = 0;
  for (const sample of samples) sum += ((sample - 128) / 128) ** 2;
  return Math.sqrt(sum / samples.length);
}
export function shouldStop(started: number, lastSound: number, now: number): boolean {
  return now - started >= MAX_CLIP_MS || (now - started > 2000 && now - lastSound > 1500);
}
