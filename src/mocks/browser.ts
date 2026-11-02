import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
export const worker = setupWorker(...handlers);
let started: ReturnType<typeof worker.start> | undefined;
export function startMocks() {
  started ??= worker.start({
    quiet: true,
    onUnhandledFrame: 'bypass',
    serviceWorker: { url: '/mockServiceWorker.js' },
  });
  return started;
}
