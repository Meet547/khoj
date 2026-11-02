import { z } from 'zod';
import { locales } from '@/lib/i18n/config';
export const userSchema = z.object({
  id: z.uuid(),
  role: z.enum(['citizen', 'volunteer', 'officer', 'admin']),
  lang: z.enum(locales.map(({ code }) => code)),
  phoneSuffix: z
    .string()
    .regex(/^\d{2}$/)
    .optional(),
});
export const authSchema = z.object({ user: userSchema });
export const otpSendRequestSchema = z.object({ phone: z.string().regex(/^[6-9]\d{9}$/) });
export const otpVerifyRequestSchema = otpSendRequestSchema.extend({
  code: z.string().regex(/^\d{6}$/),
});
export const otpSendSchema = z.object({ ok: z.literal(true), demo: z.boolean() });
