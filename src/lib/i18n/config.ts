export const locales = [
  { code: 'hi', label: 'हिन्दी' },
  { code: 'mr', label: 'मराठी' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'pa', label: 'ਪੰਜਾਬੀ' },
  { code: 'gu', label: 'ગુજરાતી' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'ml', label: 'മലയാളം' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'en', label: 'English' },
] as const;
export type Lang = (typeof locales)[number]['code'];
export function isLang(value: unknown): value is Lang {
  return locales.some(({ code }) => code === value);
}
export const isTranslated = (lang: Lang) => lang === 'en' || lang === 'hi';
