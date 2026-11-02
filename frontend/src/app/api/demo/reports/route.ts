import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { kindSchema } from '@/lib/api/types';
import { saveCase, state } from '@/mocks/server/state';
import { guard, currentUser, failure } from '@/mocks/server/http';
export async function POST(request: NextRequest) {
  const denied = guard(request);
  if (denied) return denied;
  const user = currentUser(request);
  if (!user) return failure('unauthorized', 'Please sign in.', 401);
  const parsed = z
    .object({ sessionId: z.uuid(), kind: kindSchema })
    .safeParse(await request.json().catch(() => null));
  if (!parsed.success) return failure('invalid_request', 'Please check your report.', 422);
  const existing = [...state.cases.values()].find(
    (item) => item.sessionId === parsed.data.sessionId,
  );
  if (existing && existing.ownerId !== user.id)
    return failure('not_found', 'This case is unavailable.', 404);
  const intake = state.intakes.get(parsed.data.sessionId);
  if (
    !existing &&
    (!intake ||
      intake.kind !== parsed.data.kind ||
      intake.stage !== 'confirmed' ||
      intake.expires < Date.now())
  )
    return failure('review_required', 'Please confirm the read-back before saving.', 409);
  return NextResponse.json(
    { caseNo: saveCase(user, parsed.data.kind, parsed.data.sessionId) },
    { headers: { 'Cache-Control': 'no-store' } },
  );
}
