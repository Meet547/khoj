'use client';
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { AuthProvider } from '@/features/auth/AuthProvider';
import type { Lang } from '@/lib/i18n/config';
import { readLanguage, readMode, saveLanguage, saveMode } from '@/lib/storage/prefs';
import { loadMessages } from '@/lib/i18n/messages';
type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  languageChosen: boolean;
  preferencesReady: boolean;
  mode: 'voice' | 'text';
  setMode: (m: 'voice' | 'text') => void;
  toast: (s: string) => void;
};
const Context = createContext<Ctx>(null!);
export const useApp = () => useContext(Context);
export function Providers({
  children,
  initialLang = 'en',
  initialChoice = false,
  initialMessages,
}: {
  children: ReactNode;
  initialLang?: Lang;
  initialChoice?: boolean;
  initialMessages: Record<string, string>;
}) {
  const [messages, setMessages] = useState(initialMessages);
  const selection = useRef(0);
  const [lang, setLanguage] = useState<Lang>(initialLang);
  const [languageChosen, setChosen] = useState(initialChoice);
  const [preferencesReady, setPreferencesReady] = useState(false);
  const [mode, setModeState] = useState<'voice' | 'text'>('text');
  const [notice, setNotice] = useState('');
  async function selectLanguage(value: Lang) {
    const current = ++selection.current;
    try {
      const next = await loadMessages(value);
      if (current !== selection.current) return;
      setMessages(next);
      setLanguage(value);
      setChosen(true);
      saveLanguage(value);
    } catch {
      setNotice(messages.languageLoadError || 'Please try choosing your language again.');
    }
  }
  useEffect(() => {
    const saved = readLanguage();
    if (saved) {
      setChosen(true);
      saveLanguage(saved);
      if (saved !== initialLang) void selectLanguage(saved);
    }
    setModeState(readMode());
    setPreferencesReady(true);
    if ('serviceWorker' in navigator) {
      // MSW and the offline shell must not race for the same service-worker scope.
      if (process.env.NODE_ENV === 'production' && process.env.NEXT_PUBLIC_USE_MOCK === '0')
        navigator.serviceWorker.register('/sw.js').catch(() => {});
      else
        navigator.serviceWorker
          .getRegistrations()
          .then((registrations) =>
            registrations.forEach((reg) => {
              if (reg.active?.scriptURL === location.origin + '/sw.js') void reg.unregister();
            }),
          )
          .catch(() => {});
    }
  }, []);
  useEffect(() => {
    if (document.documentElement.lang !== lang) document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(''), 4500);
    return () => clearTimeout(id);
  }, [notice]);
  return (
    <Context.Provider
      value={{
        lang,
        languageChosen,
        preferencesReady,
        setLang: (value) => {
          void selectLanguage(value);
        },
        mode,
        setMode: (value) => {
          setModeState(value);
          saveMode(value);
        },
        toast: setNotice,
      }}
    >
      <NextIntlClientProvider locale={lang} messages={messages} timeZone="Asia/Kolkata">
        <div
          className="sr-only"
          data-announcer
          role="status"
          aria-live="polite"
          aria-atomic="true"
        />
        <AuthProvider>{children}</AuthProvider>
        {notice && (
          <div className="toast" role="status">
            {notice}
          </div>
        )}
      </NextIntlClientProvider>
    </Context.Provider>
  );
}
