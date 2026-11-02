import { NextRequest, NextResponse } from 'next/server';
import { otpSendRequestSchema, otpVerifyRequestSchema } from '@/lib/api/types';
import { state, digest, limit, getUser, issue, verifyCode } from '@/mocks/server/state';
import { guard, failure, currentUser, setCookies } from '@/mocks/server/http';
export const runtime = 'nodejs';
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ action: string[] }> },
) {
  const denied = guard(request);
  if (denied) return denied;
  const { action } = await params;
  if (action.join('/') !== 'me') return failure('not_found', 'Not found.', 404);
  const user = currentUser(request);
  return user
    ? NextResponse.json({ user }, { headers: { 'Cache-Control': 'no-store' } })
    : failure('unauthorized', 'Please sign in to continue.', 401);
}
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ action: string[] }> },
) {
  const denied = guard(request);
  if (denied) return denied;
  const action = (await params).action.join('/');
  if (action === 'otp/send' || action === 'otp/verify') {
    const body: unknown = await request.json().catch(() => null);
    const parsed = (
      action === 'otp/send' ? otpSendRequestSchema : otpVerifyRequestSchema
    ).safeParse(body);
    if (!parsed.success)
      return failure(
        'invalid_request',
        'Enter a valid 10-digit Indian mobile number and code.',
        422,
      );
    const phone = parsed.data.phone,
      key = digest(phone),
      remaining = limit(action + ':' + key, action === 'otp/send' ? 5 : 10);
    if (remaining)
      return failure(
        'rate_limited',
        'Too many attempts. Please try again later.',
        429,
        true,
        remaining,
      );
    if (action === 'otp/send') {
      state.challenges.set(key, Date.now() + 300000);
      return NextResponse.json(
        { ok: true, demo: true },
        { headers: { 'Cache-Control': 'no-store' } },
      );
    }
    const verified = otpVerifyRequestSchema.parse(body);
    if ((state.challenges.get(key) || 0) <= Date.now() || !verifyCode(verified.code))
      return failure('invalid_code', "That code didn't match. Try again.", 400);
    state.challenges.delete(key);
    const user = getUser(phone);
    return setCookies(NextResponse.json({ user }), issue(user));
  }
  if (action === 'logout') {
    for (const raw of [
      request.cookies.get('khoj_session')?.value,
      request.cookies.get('khoj_refresh')?.value,
    ]) {
      if (!raw) continue;
      const entry = state.access.get(digest(raw)) || state.refresh.get(digest(raw));
      if (entry) entry.family.revoked = true;
    }
    const response = new NextResponse(null, { status: 204 });
    response.cookies.set('khoj_session', '', {
      path: '/',
      maxAge: 0,
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
    });
    response.cookies.set('khoj_refresh', '', {
      path: '/api/auth',
      maxAge: 0,
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
    });
    response.headers.set('Cache-Control', 'no-store');
    return response;
  }
  if (action === 'refresh') {
    const raw = request.cookies.get('khoj_refresh')?.value;
    const token = raw ? state.refresh.get(digest(raw)) : undefined;
    if (token?.consumed) token.family.revoked = true;
    if (!token || token.consumed || token.family.revoked || token.family.expires <= Date.now())
      return failure('unauthorized', 'Please sign in again.', 401);
    token.consumed = true;
    return setCookies(
      NextResponse.json({ user: token.family.user }),
      issue(token.family.user, token.family),
    );
  }
  return failure('not_found', 'Not found.', 404);
}
