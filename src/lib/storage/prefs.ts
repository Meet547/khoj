import { isLang, type Lang } from '@/lib/i18n/config';
export const LANGUAGE_KEY = 'khoj-language';
export function readLanguage(): Lang | undefined {
  try {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    if (isLang(saved)) return saved;
  } catch {
    /* Cookies still support preferences if storage is unavailable. */
  }
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${LANGUAGE_KEY}=`))
    ?.split('=')[1];
  return isLang(cookie) ? cookie : undefined;
}
export function saveLanguage(lang: Lang): void {
  try {
    localStorage.setItem(LANGUAGE_KEY, lang);
  } catch {
    /* Cookie fallback. */
  }
  document.cookie = `${LANGUAGE_KEY}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
}
export function readMode(): 'text' | 'voice' {
  try {
    return localStorage.getItem('khoj-mode') === 'voice' ? 'voice' : 'text';
  } catch {
    return 'text';
  }
}
export function saveMode(mode: 'text' | 'voice'): void {
  try {
    localStorage.setItem('khoj-mode', mode);
  } catch {
    /* Optional preference. */
  }
}
