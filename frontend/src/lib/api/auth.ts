import { z } from 'zod';
import { request } from './client';
import {
  authSchema,
  otpSendSchema,
  otpSendRequestSchema,
  otpVerifyRequestSchema,
} from './schemas/auth';
export const authApi = {
  me: () => request('/auth/me', authSchema, { mockInit: false }),
  logout: () => request('/auth/logout', z.undefined(), { method: 'POST', mockInit: false }),
  refresh: () => request('/auth/refresh', authSchema, { method: 'POST', mockInit: false }),
  sendOtp: (phone: string) =>
    request('/auth/otp/send', otpSendSchema, {
      body: otpSendRequestSchema.parse({ phone }),
      mockInit: false,
    }),
  verifyOtp: (phone: string, code: string) =>
    request('/auth/otp/verify', authSchema, {
      body: otpVerifyRequestSchema.parse({ phone, code }),
      mockInit: false,
    }),
};
