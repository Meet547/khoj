import { NextRequest, NextResponse } from 'next/server';
import { state } from '@/mocks/server/state';
import { guard, currentUser, failure } from '@/mocks/server/http';
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ caseNo: string }> },
) {
  const denied = guard(request);
  if (denied) return denied;
  const user = currentUser(request);
  if (!user) return failure('unauthorized', 'Please sign in.', 401);
  const item = state.cases.get((await params).caseNo);
  if (!item || item.ownerId !== user.id)
    return failure('not_found', 'This case is unavailable.', 404);
  const { ownerId: _owner, sessionId: _session, kind: _kind, caseNo: _number, ...result } = item;
  return NextResponse.json(result, { headers: { 'Cache-Control': 'no-store' } });
}
