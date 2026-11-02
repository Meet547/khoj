import { z } from 'zod';
import { errorSchema } from './schemas/error';
export const MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== '0';
export class AppError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryable: boolean,
    public retryAfter?: number,
  ) {
    super(message);
    this.name = 'AppError';
  }
}
export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  signal?: AbortSignal;
  idempotencyKey?: string;
  mockInit?: boolean;
}
let starting: Promise<unknown> | undefined;
export async function initializeMocks(): Promise<void> {
  if (!MOCK || typeof window === 'undefined') return;
  starting ??= import('#mock-client').then(({ startMocks }) => startMocks());
  try {
    await starting;
  } catch {
    starting = undefined;
    throw new AppError('mock_unavailable', 'The demo could not start. Please reload.', true);
  }
}
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestOptions = {},
): Promise<T> {
  if (options.mockInit !== false) await initializeMocks();
  const base = (
    process.env.NEXT_PUBLIC_API_BASE ||
    (typeof window === 'undefined' ? 'http://localhost:3000' : window.location.origin)
  ).replace(/\/$/, '');
  const form = options.body instanceof FormData;
  const method = options.method || (options.body === undefined ? 'GET' : 'POST');
  let response: Response;
  try {
    response = await fetch(`${base}/api${path}`, {
      method,
      credentials: 'include',
      cache: 'no-store',
      signal: options.signal,
      headers: {
        Accept: 'application/json',
        ...(!form && options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(method === 'POST'
          ? { 'Idempotency-Key': options.idempotencyKey || crypto.randomUUID() }
          : {}),
      },
      body:
        options.body === undefined
          ? undefined
          : options.body instanceof FormData
            ? options.body
            : JSON.stringify(options.body),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new AppError(
      typeof navigator !== 'undefined' && navigator.onLine === false ? 'offline' : 'network',
      'Please check your connection and try again.',
      true,
    );
  }
  if (response.status === 204) return schema.parse(undefined);
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new AppError(
      'invalid_response',
      'The service sent an unexpected response. Please try again.',
      true,
    );
  }
  if (!response.ok) {
    const parsed = errorSchema.safeParse(data);
    const seconds = Number(response.headers.get('Retry-After'));
    throw new AppError(
      parsed.success ? parsed.data.error.code : `http_${response.status}`,
      parsed.success
        ? parsed.data.error.message
        : 'The service could not complete this request. Please try again.',
      parsed.success
        ? parsed.data.error.retryable
        : response.status === 429 || response.status >= 500,
      Number.isFinite(seconds) && seconds > 0 ? seconds : undefined,
    );
  }
  const result = schema.safeParse(data);
  if (!result.success)
    throw new AppError(
      'invalid_response',
      'The service sent an unexpected response. Please try again.',
      false,
    );
  return result.data;
}
