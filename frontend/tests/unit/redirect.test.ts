import { it, expect } from 'vitest';
import { safeNext } from '@/features/auth/redirect';
it.each([
  'https://attacker.example',
  '//attacker.example',
  '/%2f%2fattacker.example',
  '/\\attacker.example',
  '/login?next=//evil',
  'javascript:alert(1)',
  '/\n/evil',
])('rejects unsafe login redirect %s', (path) => {
  expect(safeNext(path)).toBe('/cases');
});
it('preserves a local destination and query string', () => {
  expect(safeNext('/case/KHJ-2026-00001?tab=timeline')).toBe('/case/KHJ-2026-00001?tab=timeline');
});
