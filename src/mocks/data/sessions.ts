import type { Lang, Kind, PersonDraft, Turn } from '@/lib/api/types';
import { extractDemoDescription } from './extract';
export interface MockSession {
  draft: PersonDraft;
  lang: Lang;
  reviewed: boolean;
  index: number;
}
export const sessions = new Map<string, MockSession>();
export const response = (
  session: MockSession,
  transcript = '',
  stage: Turn['stage'] = 'readback',
): Turn => ({
  transcript,
  replyText: session.lang === 'hi' ? 'कृपया विवरण जांचें।' : 'Please review the details.',
  draft: structuredClone(session.draft),
  stage,
});
export function createSession(kind: Kind, lang: Lang) {
  const id = crypto.randomUUID();
  sessions.set(id, { draft: { kind, fieldConfidence: {} }, lang, reviewed: false, index: 0 });
  return id;
}
export function turn(session: MockSession, text: string): Turn {
  const edit =
    /^Update (name|gender|age|marks|language|clothing|place|time|conditions): ([\s\S]*)$/.exec(
      text,
    );
  if (edit) {
    const field = edit[1] as
      | 'name'
      | 'gender'
      | 'age'
      | 'marks'
      | 'language'
      | 'clothing'
      | 'place'
      | 'time'
      | 'conditions';
    session.reviewed = false;
    if (field === 'conditions') session.draft.conditions = edit[2] ? [edit[2]] : [];
    else if (edit[2].trim()) session.draft[field] = edit[2];
    else delete session.draft[field];
    session.draft.fieldConfidence[field] = 1;
    return response(session, text, session.index ? 'readback' : 'collecting');
  }
  if (['Yes, that’s correct', 'हाँ, यह सही है'].includes(text)) {
    if (!session.index) throw new Error('Please complete and review the description first.');
    session.reviewed = true;
    return response(session, '', 'confirmed');
  }
  if (!text.trim()) throw new Error('Describe the person before continuing.');
  session.draft = { kind: session.draft.kind, ...extractDemoDescription(text) };
  session.index = 1;
  session.reviewed = false;
  return {
    ...response(session, text),
    readbackText: Object.values(session.draft)
      .filter((v) => typeof v === 'string')
      .join(', '),
  };
}
