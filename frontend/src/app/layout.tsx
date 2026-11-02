import type { Metadata, Viewport } from 'next';
import localFont from 'next/font/local';
import { cookies } from 'next/headers';
import { loadMessages } from '@/lib/i18n/messages';
import { isLang } from '@/lib/i18n/config';
import { Providers } from '@/components/providers';
import { Header, Footer } from '@/components/layout/index';
import '@/styles/globals.css';
const display = localFont({
  src: '../../public/fonts/display-latin.woff2',
  variable: '--font-display',
  adjustFontFallback: 'Times New Roman',
  fallback: ['Georgia', 'serif'],
  display: 'swap',
});
const hind = localFont({
  src: [
    { path: '../../public/fonts/hind-regular.woff2', weight: '400' },
    { path: '../../public/fonts/hind-semibold.woff2', weight: '600' },
  ],
  variable: '--font-hind',
  display: 'swap',
  preload: false,
});
const geist = localFont({
  src: '../../public/fonts/geist-latin.woff2',
  variable: '--font-geist',
  display: 'swap',
});
const devanagari = localFont({
  src: '../../public/fonts/indic/devanagari.woff2',
  variable: '--font-devanagari',
  display: 'swap',
  preload: false,
});
const bengali = localFont({
  src: '../../public/fonts/indic/bengali.woff2',
  variable: '--font-bengali',
  display: 'swap',
  preload: false,
});
const tamil = localFont({
  src: '../../public/fonts/indic/tamil.woff2',
  variable: '--font-tamil',
  display: 'swap',
  preload: false,
});
const gurmukhi = localFont({
  src: '../../public/fonts/indic/gurmukhi.woff2',
  variable: '--font-gurmukhi',
  display: 'swap',
  preload: false,
});
const gujarati = localFont({
  src: '../../public/fonts/indic/gujarati.woff2',
  variable: '--font-gujarati',
  display: 'swap',
  preload: false,
});
const kannada = localFont({
  src: '../../public/fonts/indic/kannada.woff2',
  variable: '--font-kannada',
  display: 'swap',
  preload: false,
});
const malayalam = localFont({
  src: '../../public/fonts/indic/malayalam.woff2',
  variable: '--font-malayalam',
  display: 'swap',
  preload: false,
});
const telugu = localFont({
  src: '../../public/fonts/indic/telugu.woff2',
  variable: '--font-telugu',
  display: 'swap',
  preload: false,
});
export const metadata: Metadata = {
  title: { default: 'KHOJ — Every search matters.', template: '%s · KHOJ' },
  description:
    'A little hope. A collective effort. Report a missing person, report someone found, or search by description. KHOJ frontend demo.',
  manifest: '/manifest.webmanifest',
  icons: { icon: '/icon.svg', apple: '/icon-192.png' },
};
export const viewport: Viewport = { themeColor: '#f1f2ec', width: 'device-width', initialScale: 1 };
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const preference = (await cookies()).get('khoj-language')?.value;
  const lang = isLang(preference) ? preference : 'en';
  const messages = await loadMessages(lang);
  return (
    <html
      lang={lang}
      className={`${display.variable} ${geist.variable} ${hind.variable} ${devanagari.variable} ${bengali.variable} ${tamil.variable} ${gurmukhi.variable} ${gujarati.variable} ${kannada.variable} ${malayalam.variable} ${telugu.variable}`}
    >
      <body>
        <Providers initialLang={lang} initialChoice={isLang(preference)} initialMessages={messages}>
          <div className="page-scroll">
            <Header />
            {children}
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
