import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { validAccess } from './state';
export function failure(
  code: string,
  message: string,
  status: number,
  retryable = false,
  retryAfter?: number,
) {
  return NextResponse.json(
    { error: { code, message, retryable } },
    {
      status,
      headers: {
        'Cache-Control': 'no-store',
        ...(retryAfter ? { 'Retry-After': String(retryAfter) } : {}),
      },
    },
  );
}
export function guard(request: NextRequest) {
  if (process.env.NEXT_PUBLIC_USE_MOCK === '0' || process.env.KHOJ_ENV === 'production')
    return failure('not_found', 'Demo endpoints are disabled.', 404);
  if (request.method !== 'GET') {
    const origin = request.headers.get('origin');
    let sameHost = true;
    if (origin) {
      try {
        const parsed = new URL(origin);
        sameHost =
          ['http:', 'https:'].includes(parsed.protocol) &&
          parsed.host === request.headers.get('host') &&
          !parsed.username &&
          !parsed.password;
      } catch {
        sameHost = false;
      }
    }
    if (!sameHost || request.headers.get('sec-fetch-site') === 'cross-site')
      return failure('forbidden', 'This request could not be verified.', 403);
  }
  return null;
}
export function currentUser(request: NextRequest) {
  return validAccess(request.cookies.get('khoj_session')?.value);
}
export function setCookies(response: NextResponse, tokens: { access: string; refresh: string }) {
  response.cookies.set('khoj_session', tokens.access, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 900,
  });
  response.cookies.set('khoj_refresh', tokens.refresh, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/api/auth',
    maxAge: 7 * 86400,
  });
  response.headers.set('Cache-Control', 'no-store');
  return response;
}
