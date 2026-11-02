import { z } from 'zod';
import { request, MOCK } from './client';
import { endpoints as e } from './endpoints';
import * as s from './types';
export { MOCK, AppError } from './client';
export type {
  Lang,
  Kind,
  Stage,
  PersonDraft,
  Turn,
  Hit,
  SearchResult,
  CaseStatus,
  User,
} from './types';
export const api = {
  session: (lang: s.Lang, kind: s.Kind) =>
    request(e.session, s.sessionSchema, { body: s.sessionRequestSchema.parse({ lang, kind }) }),
  turn: (sessionId: string, input: { text?: string; audio?: Blob; clipIndex?: number }) => {
    const form = new FormData();
    form.set('sessionId', sessionId);
    if (input.text !== undefined) form.set('text', input.text);
    if (input.audio) form.set('audio', input.audio, 'recording.webm');
    if (input.clipIndex !== undefined) form.set('clipIndex', String(input.clipIndex));
    return request(e.turn, s.turnSchema, { body: form });
  },
  edit: (sessionId: string, field: z.infer<typeof s.fieldSchema>, value: string | string[]) =>
    request(e.draftEdit, s.turnSchema, {
      body: s.draftEditRequestSchema.parse({ sessionId, field, value }),
    }),
  restore: async (
    sessionId: string,
    draft: s.PersonDraft,
    index: number,
    lang: s.Lang,
    reviewed = false,
  ) => {
    if (MOCK)
      await request('/__mock/draft/restore', s.okSchema, {
        body: { sessionId, draft, index, lang, reviewed },
      });
  },
  photos: (sessionId: string, files: File[]) => {
    const form = new FormData();
    form.set('sessionId', sessionId);
    files.forEach((file) => form.append('files', file));
    return request(e.photos, s.photosSchema, { body: form });
  },
  confirm: (sessionId: string) => request(e.confirm, s.confirmSchema, { body: { sessionId } }),
  search: (query: string, filters: Record<string, string>, signal?: AbortSignal, refresh = false) =>
    request(e.search, s.searchSchema, { body: { query, filters, refresh }, signal }),
  case: (caseNo: string) =>
    request(`/case/${encodeURIComponent(caseNo)}`, s.caseSchema, { mockInit: false }),
  cases: () => request(e.cases, s.casesSchema, { mockInit: false }),
  sendOtp: (phone: string) =>
    request(e.otpSend, s.otpSendSchema, {
      body: s.otpSendRequestSchema.parse({ phone }),
      mockInit: false,
    }),
  verifyOtp: (phone: string, code: string) =>
    request(e.otpVerify, s.authSchema, {
      body: s.otpVerifyRequestSchema.parse({ phone, code }),
      mockInit: false,
    }),
  me: () => request(e.me, s.authSchema, { mockInit: false }),
  logout: () => request(e.logout, z.undefined(), { method: 'POST', mockInit: false }),
  refresh: () => request(e.refresh, s.authSchema, { method: 'POST', mockInit: false }),
  stt: (audio: Blob, lang: s.Lang) => {
    const form = new FormData();
    form.set('audio', audio, 'recording.webm');
    form.set('lang', lang);
    return request(e.stt, s.sttSchema, { body: form });
  },
  tts: (text: string, lang: s.Lang) => request(e.tts, s.ttsSchema, { body: { text, lang } }),
};
