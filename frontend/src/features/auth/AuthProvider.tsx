'use client';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';
const getApi = async () => (await import('@/lib/api/auth')).authApi;
import type { User } from '@/lib/api/types';
export type AuthStatus = 'loading' | 'guest' | 'authenticated' | 'error';
interface AuthContext {
  user: User | null;
  loggingOut: boolean;
  status: AuthStatus;
  error: string;
  login: (phone: string, code: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}
const Context = createContext<AuthContext | null>(null);
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error('AuthProvider is required');
  return value;
}
export function AuthProvider({ children }: { children: ReactNode }) {
  const path = usePathname();
  const generation = useRef(0);
  const [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => setLoggingOut(false), [path]);
  const [user, setUser] = useState<User | null>(null),
    [status, setStatus] = useState<AuthStatus>('loading'),
    [error, setError] = useState('');
  const refresh = useCallback(async () => {
    const current = ++generation.current;
    setError('');
    try {
      const result = await (await getApi()).me();
      if (current !== generation.current) return;
      setUser(result.user);
      setStatus('authenticated');
    } catch (e) {
      if (current !== generation.current) return;
      if (e instanceof Error && 'code' in e && e.code === 'unauthorized') {
        setUser(null);
        setStatus('guest');
      } else {
        setError(e instanceof Error ? e.message : 'Please try again.');
        setStatus('error');
      }
    }
  }, []);
  useEffect(() => {
    try {
      localStorage.removeItem('khoj-cases');
    } catch {
      /* Remove legacy demo phone references when storage permits. */
    }
    const initial = generation.current;
    const run = () => {
      if (generation.current === initial) void refresh();
    };
    if (path === '/' && 'requestIdleCallback' in window) {
      const task = window.requestIdleCallback(run, { timeout: 1000 });
      return () => window.cancelIdleCallback(task);
    }
    void refresh();
  }, [refresh]);
  const login = useCallback(async (phone: string, code: string) => {
    const result = await (await getApi()).verifyOtp(phone, code);
    generation.current++;
    setLoggingOut(false);
    const authenticated = {
      ...result.user,
      phoneSuffix: result.user.phoneSuffix || phone.slice(-2),
    };
    setUser(authenticated);
    setError('');
    setStatus('authenticated');
    return authenticated;
  }, []);
  const logout = useCallback(async () => {
    generation.current++;
    setLoggingOut(true);
    try {
      await (await getApi()).logout();
      setUser(null);
      setStatus('guest');
    } catch (e) {
      setLoggingOut(false);
      throw e;
    }
  }, []);
  return (
    <Context.Provider value={{ user, status, error, loggingOut, login, logout, refresh }}>
      {children}
    </Context.Provider>
  );
}
