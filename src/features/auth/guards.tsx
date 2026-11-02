'use client';
import { useEffect, type ReactNode } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from './useAuth';
import type { User } from '@/lib/api';
export function useRequireAuth() {
  const auth = useAuth(),
    router = useRouter(),
    path = usePathname();
  useEffect(() => {
    if (auth.status === 'guest' && !auth.loggingOut)
      router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [auth.status, auth.loggingOut, path, router]);
  return auth;
}
export function RequireRole({ role, children }: { role: User['role']; children: ReactNode }) {
  const { user, status } = useAuth();
  const t = useTranslations();
  if (status === 'loading') return <p role="status">{t('loading')}</p>;
  return user && (user.role === role || user.role === 'admin') ? (
    <>{children}</>
  ) : (
    <p>{t('notAvailableDemo')}</p>
  );
}
