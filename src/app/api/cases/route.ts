import { NextRequest, NextResponse } from 'next/server';
import { state } from '@/mocks/server/state';
import { guard, currentUser, failure } from '@/mocks/server/http';
export async function GET(request: NextRequest) {
  const denied = guard(request);
  if (denied) return denied;
  const user = currentUser(request);
  if (!user) return failure('unauthorized', 'Please sign in.', 401);
  const cases = [...state.cases.values()]
    .filter((c) => c.ownerId === user.id)
    .map(({ ownerId: _owner, sessionId: _session, ...item }) => item);
  return NextResponse.json({ cases }, { headers: { 'Cache-Control': 'no-store' } });
}
