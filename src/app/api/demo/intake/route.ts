import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { kindSchema } from '@/lib/api/types';
import { state } from '@/mocks/server/state';
import { guard, failure } from '@/mocks/server/http';
export async function POST(request: NextRequest) {
  const denied = guard(request);
  if (denied) return denied;
  const parsed = z
    .object({
      sessionId: z.uuid(),
      kind: kindSchema,
      stage: z.enum(['collecting', 'readback', 'confirmed']),
    })
    .safeParse(await request.json().catch(() => null));
  if (!parsed.success) return failure('invalid_request', 'Please check the report.', 422);
  const body = parsed.data,
    previous = state.intakes.get(body.sessionId);
  if (
    body.stage === 'confirmed' &&
    (!previous ||
      previous.kind !== body.kind ||
      (previous.stage !== 'readback' && previous.stage !== 'confirmed'))
  )
    return failure('review_required', 'Please review the description first.', 409);
  state.intakes.set(body.sessionId, {
    kind: body.kind,
    stage: body.stage,
    expires: Date.now() + 86400000,
  });
  return NextResponse.json({ ok: true }, { headers: { 'Cache-Control': 'no-store' } });
}
