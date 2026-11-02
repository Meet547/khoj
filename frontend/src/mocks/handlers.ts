import { http, HttpResponse, delay, passthrough } from 'msw';
import { z } from 'zod';
import * as schemas from '@/lib/api/types';
import { request as apiRequest } from '@/lib/api/client';
import { sessions, createSession, turn } from './data/sessions';
const path = (value: string) => `*/api${value}`;
const scenario = () =>
  typeof location === 'undefined' ? '' : new URLSearchParams(location.search).get('mock') || '';
const error = (code: string, message: string, status = 400, retryable = false) =>
  HttpResponse.json({ error: { code, message, retryable } }, { status });
async function wait(ms: number) {
  await delay(scenario() === 'slow' ? ms * 4 : ms);
}
async function syncIntake(
  sessionId: string,
  session: { draft: schemas.PersonDraft },
  stage: 'collecting' | 'readback' | 'confirmed',
) {
  await apiRequest('/demo/intake', schemas.okSchema, {
    body: { sessionId, kind: session.draft.kind, stage },
    mockInit: false,
  });
}
const unavailable = () =>
  scenario() === 'error'
    ? error('unavailable', 'The service is busy. Please try again.', 503, true)
    : null;
export const handlers = [
  // HttpOnly auth cookies can only be issued by the same-origin mock server bridge.
  http.all(path('/auth/*'), () => passthrough()),
  http.all(path('/demo/*'), () => passthrough()),
  http.get(path('/cases'), () => passthrough()),
  http.get(path('/case/:caseNo'), () => passthrough()),
  http.post(path('/session'), async ({ request }) => {
    await wait(300);
    const failure = unavailable();
    if (failure) return failure;
    const parsed = schemas.sessionRequestSchema.safeParse(await request.json());
    if (!parsed.success || !['missing', 'found'].includes(parsed.data.kind))
      return error('invalid_request', 'Please choose a report type.', 422);
    return HttpResponse.json({
      sessionId: createSession(parsed.data.kind as schemas.Kind, parsed.data.lang),
    });
  }),
  http.post(path('/turn'), async ({ request }) => {
    await wait(2000);
    const failure = unavailable();
    if (failure) return failure;
    const form = await request.formData();
    const session = sessions.get(String(form.get('sessionId')));
    if (!session) return error('session_expired', 'This demo session expired. Please start again.');
    if (form.get('audio'))
      return error(
        'stt_unavailable',
        session.lang === 'hi'
          ? 'डेमो में आवाज़ की पहचान उपलब्ध नहीं है। कृपया लिखें।'
          : 'Speech transcription needs a connected backend. Please type your answer in this demo.',
        503,
      );
    try {
      const result = turn(session, String(form.get('text') || ''));
      if (scenario() === 'lowconfidence')
        Object.keys(result.draft.fieldConfidence).forEach(
          (key) => (result.draft.fieldConfidence[key] = 0.4),
        );
      await syncIntake(
        String(form.get('sessionId')),
        session,
        result.stage === 'confirmed'
          ? 'confirmed'
          : result.stage === 'readback'
            ? 'readback'
            : 'collecting',
      );
      return HttpResponse.json(result);
    } catch (e) {
      return error(
        'review_required',
        e instanceof Error ? e.message : 'Please check your description.',
      );
    }
  }),
  http.post(path('/draft/edit'), async ({ request }) => {
    await wait(300);
    const parsed = schemas.draftEditRequestSchema.safeParse(await request.json());
    if (!parsed.success) return error('invalid_request', 'Please check the field.', 422);
    const { sessionId, field, value } = parsed.data;
    const session = sessions.get(sessionId);
    if (!session) return error('session_expired', 'Please start again.');
    const result = turn(
      session,
      `Update ${field}: ${Array.isArray(value) ? value.join(', ') : value}`,
    );
    await syncIntake(sessionId, session, 'readback');
    return HttpResponse.json(result);
  }),
  http.post(path('/__mock/draft/restore'), async ({ request }) => {
    const body = z
      .object({
        sessionId: z.uuid(),
        draft: schemas.draftSchema,
        index: z.number().int(),
        lang: schemas.langSchema,
        reviewed: z.boolean(),
      })
      .safeParse(await request.json());
    if (!body.success) return error('invalid_request', 'This draft cannot be restored.', 422);
    const { sessionId, ...session } = body.data;
    sessions.set(sessionId, session);
    await syncIntake(sessionId, session, session.index ? 'readback' : 'collecting');
    if (session.reviewed) await syncIntake(sessionId, session, 'confirmed');
    return HttpResponse.json({ ok: true });
  }),
  http.post(path('/photos'), async ({ request }) => {
    await wait(500);
    const form = await request.formData();
    return HttpResponse.json({ photoIds: form.getAll('files').map(() => crypto.randomUUID()) });
  }),
  http.post(path('/confirm'), async ({ request }) => {
    await wait(700);
    const body = z.object({ sessionId: z.uuid() }).safeParse(await request.json());
    const session = body.success ? sessions.get(body.data.sessionId) : undefined;
    if (!session?.reviewed)
      return error('review_required', 'Please confirm the report before saving.');
    try {
      await apiRequest('/auth/me', schemas.authSchema, { mockInit: false });
      const result = await apiRequest('/demo/reports', schemas.confirmSchema, {
        body: { kind: session.draft.kind, sessionId: body.success ? body.data.sessionId : '' },
        mockInit: false,
      });
      return HttpResponse.json(result);
    } catch (e) {
      return error('unauthorized', e instanceof Error ? e.message : 'Please sign in.', 401);
    }
  }),
  http.post(path('/search'), async ({ request }) => {
    await wait(3000);
    const failure = unavailable();
    if (failure) return failure;
    const body = z
      .object({ query: z.string(), filters: z.record(z.string(), z.string()) })
      .parse(await request.json());
    const empty = scenario() === 'empty' || /no match|empty/i.test(body.query);
    return HttpResponse.json({
      source: 'cache',
      checkedAt: new Date().toISOString(),
      scanned: 120,
      hits: empty
        ? []
        : ['Strong', 'Possible', 'Weak'].map((band, i) => ({
            band,
            record: {
              placeOfMissing: body.filters.district || 'Demo location',
              policeStation: `Demo station ${i + 1}`,
              district: body.filters.district || 'Demo district',
              state: body.filters.state || 'DELHI',
              ddDate: '2026-10-25',
              status: 'Untraced',
              details: { age: 'About 24 years', reference: `DEMO-${i + 1}` },
            },
            reasons:
              i === 0
                ? ['Identifying mark mentioned in physical details', 'Age range is similar']
                : ['A stated detail is similar; an officer must review it.'],
          })),
      note: 'Illustrative records only. No police records have been checked.',
      disclaimer: 'Possible match. An officer will review it before anyone is contacted.',
    });
  }),
  http.post(path('/voice/stt'), async () => {
    await wait(1500);
    if (scenario() === 'micdenied')
      return error('mic_denied', 'Please allow microphone access or continue by typing.', 403);
    return HttpResponse.json({ transcript: '', detectedLang: null, empty: true });
  }),
  http.post(path('/voice/tts'), () =>
    error('tts_unavailable', 'Speech playback is unavailable in this demo.', 503, true),
  ),
  http.get(path('/review/queue'), () => error('forbidden', 'Not available in demo.', 403)),
  http.post(path('/review/:id'), () => error('forbidden', 'Not available in demo.', 403)),
  http.get(path('/admin/health'), () => error('forbidden', 'Not available in demo.', 403)),
  http.get(path('/admin/usage'), () => error('forbidden', 'Not available in demo.', 403)),
];
