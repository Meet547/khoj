// @vitest-environment jsdom
import { it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '@/features/auth/AuthProvider';
import { authApi as api } from '@/lib/api/auth';
vi.mock('next/navigation', () => ({ usePathname: () => '/' }));
vi.mock('@/lib/api/auth', () => ({
  authApi: { me: vi.fn(), logout: vi.fn(), verifyOtp: vi.fn() },
  AppError: class extends Error {
    code = 'unauthorized';
  },
}));
afterEach(cleanup);
function Consumer() {
  const auth = useAuth();
  return (
    <>
      <output>{auth.status}</output>
      <button onClick={() => void auth.logout()}>Log out</button>
    </>
  );
}
it('ignores a stale account response that arrives after logout', async () => {
  let resolve!: (data: { user: { id: string; role: 'citizen'; lang: 'en' } }) => void;
  vi.mocked(api.me).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  vi.mocked(api.logout).mockResolvedValue(undefined);
  render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>,
  );
  await userEvent.setup().click(screen.getByRole('button', { name: 'Log out' }));
  expect(screen.getByRole('status').textContent).toBe('guest');
  await act(async () => {
    resolve({ user: { id: crypto.randomUUID(), role: 'citizen', lang: 'en' } });
  });
  expect(screen.getByRole('status').textContent).toBe('guest');
});
