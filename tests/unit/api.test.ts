import { afterEach, describe, it, expect, vi } from 'vitest';
import { z } from 'zod';
import { request, AppError } from '@/lib/api/client';
import { hitSchema, authSchema, sessionSchema } from '@/lib/api/types';
afterEach(() => vi.unstubAllGlobals());
describe('validated API client', () => {
  it('includes cookies and an idempotency key without bearer credentials', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    vi.stubGlobal('fetch', fetch);
    await request('/example', z.object({ ok: z.boolean() }), {
      body: { value: 'hello' },
      idempotencyKey: 'retry-key',
    });
    expect(fetch.mock.calls[0][1]).toMatchObject({
      credentials: 'include',
      headers: { 'Idempotency-Key': 'retry-key' },
    });
    expect(fetch.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
  });
  it('maps typed API errors and Retry-After', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: 'busy', message: 'Please try again.', retryable: true },
          }),
          { status: 429, headers: { 'Retry-After': '8' } },
        ),
      ),
    );
    await expect(request('/example', z.object({ ok: z.boolean() }))).rejects.toMatchObject({
      code: 'busy',
      retryable: true,
      retryAfter: 8,
    });
  });
  it('rejects malformed success payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ sessionId: 'not-a-uuid' }))),
    );
    await expect(request('/session', sessionSchema)).rejects.toMatchObject({
      code: 'invalid_response',
      retryable: false,
    });
  });
  it('maps network failures without echoing internal details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private network information')));
    try {
      await request('/session', sessionSchema);
      throw Error('Expected failure');
    } catch (error) {
      expect(error).toBeInstanceOf(AppError);
      expect((error as AppError).code).toBe('network');
      expect((error as Error).message).not.toContain('private');
    }
  });
  it('preserves request cancellation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('Aborted', 'AbortError')));
    await expect(request('/session', sessionSchema)).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('does not return numerical scores or restricted fields to citizens', () => {
    const hit = {
      record: {
        placeOfMissing: 'Demo place',
        policeStation: 'Demo',
        district: 'Demo',
        state: 'DELHI',
        ddDate: '2026-01-01',
        status: 'Untraced',
        details: {},
      },
      band: 'Strong',
      reasons: ['A stated mark is similar.'],
    };
    expect(hitSchema.safeParse(hit).success).toBe(true);
    expect(hitSchema.safeParse({ ...hit, score: 0.99 }).success).toBe(false);
    expect(
      hitSchema.safeParse({ ...hit, record: { ...hit.record, foundLocation: 'private' } }).success,
    ).toBe(false);
  });
  it('validates the cookie-auth user contract with no token field required', () => {
    expect(
      authSchema.parse({ user: { id: crypto.randomUUID(), role: 'citizen', lang: 'hi' } }).user
        .role,
    ).toBe('citizen');
  });
});
