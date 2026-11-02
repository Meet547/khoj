export function safeNext(value: string | null | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020]/.test(value))
    return '/cases';
  try {
    const decoded = decodeURIComponent(value);
    if (decoded.startsWith('//') || /[\\\u0000-\u0020]/.test(decoded)) return '/cases';
    const parsed = new URL(value, 'https://khoj.invalid');
    return parsed.origin === 'https://khoj.invalid' && !parsed.pathname.startsWith('/login')
      ? parsed.pathname + parsed.search + parsed.hash
      : '/cases';
  } catch {
    return '/cases';
  }
}
