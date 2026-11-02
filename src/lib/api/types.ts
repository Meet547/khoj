import { z } from 'zod';
import { userSchema } from './schemas/auth';
import { locales } from '@/lib/i18n/config';
export const langSchema = z.enum(locales.map(({ code }) => code));
export const kindSchema = z.enum(['missing', 'found']);
export const fieldSchema = z.enum([
  'name',
  'relation',
  'gender',
  'age',
  'height',
  'build',
  'complexion',
  'hair',
  'marks',
  'language',
  'clothing',
  'place',
  'time',
  'conditions',
]);
export const fieldStateSchema = z.object({
  value: z.string(),
  evidence: z.string(),
  source_turn: z.number().int().nonnegative(),
  confidence: z.enum(['high', 'confirm']),
  confirmed: z.boolean(),
});
export const draftSchema = z.object({
  kind: kindSchema,
  name: z.string().optional(),
  relation: z.string().optional(),
  gender: z.string().optional(),
  age: z.string().optional(),
  height: z.string().optional(),
  build: z.string().optional(),
  complexion: z.string().optional(),
  hair: z.string().optional(),
  marks: z.string().optional(),
  language: z.string().optional(),
  clothing: z.string().optional(),
  place: z.string().optional(),
  time: z.string().optional(),
  conditions: z.array(z.string()).optional(),
  fieldConfidence: z.record(z.string(), z.number().min(0).max(1)),
  evidence: z.record(z.string(), fieldStateSchema).optional(),
});
export const stageSchema = z.enum([
  'collecting',
  'clarify',
  'photo',
  'readback',
  'confirmed',
  'saved',
]);
export const sessionRequestSchema = z.object({
  kind: z.enum(['missing', 'found', 'search', 'status']),
  lang: langSchema,
});
export const sessionSchema = z.object({ sessionId: z.uuid() });
export const turnSchema = z.object({
  transcript: z.string(),
  replyText: z.string(),
  replyAudioUrl: z.string().nullable().optional(),
  draft: draftSchema,
  stage: stageSchema,
  nextField: z.string().nullable().optional(),
  readbackText: z.string().nullable().optional(),
});
export const draftEditRequestSchema = z.object({
  sessionId: z.uuid(),
  field: fieldSchema,
  value: z.union([z.string(), z.array(z.string())]),
});
export const photosSchema = z.object({ photoIds: z.array(z.uuid()) });
export const confirmSchema = z.object({ caseNo: z.string().regex(/^KHJ-\d{4}-\d{5,}$/) });
const recordSchema = z
  .object({
    placeOfMissing: z.string(),
    policeStation: z.string(),
    district: z.string(),
    state: z.string(),
    ddDate: z.string(),
    status: z.string(),
    imageUrl: z.string().optional(),
    details: z.record(z.string(), z.string()),
  })
  .strict();
// Deliberately excludes numerical scores and restricted found-person fields.
export const hitSchema = z
  .object({
    record: recordSchema,
    band: z.enum(['Strong', 'Possible', 'Weak', 'Listed']),
    reasons: z.array(z.string()),
  })
  .strict();
export const searchSchema = z.object({
  source: z.enum(['live', 'cache', 'stale-cache']),
  checkedAt: z.iso.datetime(),
  scanned: z.number().int().nonnegative(),
  hits: z.array(hitSchema),
  note: z.string().optional(),
  disclaimer: z.string(),
});
export const caseSchema = z.object({
  status: z.string(),
  lastCheckedAt: z.iso.datetime(),
  recordsChecked: z.number().int().nonnegative(),
  pendingReview: z.number().int().nonnegative(),
  timeline: z.array(z.object({ at: z.iso.datetime(), text: z.string() })),
});
export const casesSchema = z.object({
  cases: z.array(caseSchema.extend({ caseNo: confirmSchema.shape.caseNo, kind: kindSchema })),
});
export {
  userSchema,
  authSchema,
  otpSendRequestSchema,
  otpVerifyRequestSchema,
  otpSendSchema,
} from './schemas/auth';
export const okSchema = z.object({ ok: z.literal(true) });
export { errorSchema } from './schemas/error';
export const sttSchema = z.object({
  transcript: z.string(),
  detectedLang: langSchema.nullable(),
  empty: z.boolean(),
});
export const ttsSchema = z.object({ audioUrl: z.string() });
export const reviewQueueSchema = z.object({
  items: z.array(
    z.object({
      id: z.uuid(),
      band: z.enum(['strong', 'possible', 'weak']),
      reasons: z.array(z.string()),
      status: z.string(),
    }),
  ),
});
export const reviewRequestSchema = z.object({
  decision: z.enum(['approve', 'reject', 'needs_info']),
  note: z.string(),
});
export const healthSchema = z.object({
  ok: z.boolean(),
  checks: z.record(z.string(), z.boolean()),
});
export const usageSchema = z.object({
  roles: z.record(
    z.string(),
    z.object({
      calls: z.number().int().nonnegative(),
      tokens: z.number().int().nonnegative(),
      degraded: z.boolean(),
    }),
  ),
});
export type Lang = z.infer<typeof langSchema>;
export type Kind = z.infer<typeof kindSchema>;
export type Stage = z.infer<typeof stageSchema>;
export type PersonDraft = z.infer<typeof draftSchema>;
export type Turn = z.infer<typeof turnSchema>;
export type Hit = z.infer<typeof hitSchema>;
export type SearchResult = z.infer<typeof searchSchema>;
export type CaseStatus = z.infer<typeof caseSchema>;
export type User = z.infer<typeof userSchema>;
