// @vitest-environment jsdom
import { afterEach, it, expect, vi } from 'vitest';
import { readLanguage, saveLanguage } from '@/lib/storage/prefs';
import { isLang, locales } from '@/lib/i18n/config';
afterEach(() => {
  localStorage.clear();
  document.cookie = 'khoj-language=; Path=/; Max-Age=0';
  vi.restoreAllMocks();
});
it('supports exactly the ten speech locales', () => {
  expect(locales).toHaveLength(10);
  expect(isLang('te')).toBe(true);
  expect(isLang('or')).toBe(false);
});
it('persists the selected language in both preference stores', () => {
  saveLanguage('ta');
  expect(readLanguage()).toBe('ta');
  expect(document.cookie).toContain('khoj-language=ta');
});
it('falls back to a cookie when localStorage is blocked', () => {
  document.cookie = 'khoj-language=mr; Path=/';
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new DOMException('Blocked', 'SecurityError');
  });
  expect(readLanguage()).toBe('mr');
});
it('ignores invalid stored locales', () => {
  localStorage.setItem('khoj-language', 'invalid');
  expect(readLanguage()).toBeUndefined();
});
