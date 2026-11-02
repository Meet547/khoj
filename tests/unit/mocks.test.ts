import { afterAll, beforeAll, it, expect } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { handlers } from '@/mocks/handlers';
import { api } from '@/lib/api';
import { sessions } from '@/mocks/data/sessions';
const server = setupServer(
  http.post('*/api/demo/intake', () => HttpResponse.json({ ok: true })),
  ...handlers,
);
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
afterAll(() => server.close());
it('uses MSW transport and prevents saving before confirmed read-back', async () => {
  const { sessionId } = await api.session('en', 'missing');
  await expect(api.confirm(sessionId)).rejects.toMatchObject({ code: 'review_required' });
  const draft = await api.turn(sessionId, {
    text: 'My brother Rahul is about 24 years old. He speaks Hindi.',
  });
  expect(draft.stage).toBe('readback');
  expect(draft.draft.name).toBe('Rahul');
  await api.turn(sessionId, { text: 'Yes, that’s correct' });
  expect(sessions.get(sessionId)?.reviewed).toBe(true);
  await api.edit(sessionId, 'name', 'Rahul Sharma');
  expect(sessions.get(sessionId)?.reviewed).toBe(false);
});
it('authentication failure cannot be bypassed by a confirmed draft', async () => {
  server.use(
    http.get('*/api/auth/me', () =>
      HttpResponse.json(
        { error: { code: 'unauthorized', message: 'Please sign in.', retryable: false } },
        { status: 401 },
      ),
    ),
  );
  const { sessionId } = await api.session('hi', 'found');
  await api.restore(sessionId, { kind: 'found', fieldConfidence: {} }, 1, 'hi', true);
  await expect(api.confirm(sessionId)).rejects.toMatchObject({ code: 'unauthorized' });
});
