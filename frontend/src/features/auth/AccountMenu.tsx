'use client';
import { useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from './useAuth';
import { useApp } from '@/components/providers';
export function AccountMenu() {
  const { user, logout } = useAuth(),
    t = useTranslations(),
    { toast } = useApp(),
    router = useRouter(),
    [busy, setBusy] = useState(false),
    menu = useRef<HTMLDetailsElement | null>(null);
  if (!user) return null;
  return (
    <details className="account-menu" ref={menu}>
      <summary aria-label={`${t('account')}${user.phoneSuffix ? `: •• ${user.phoneSuffix}` : ''}`}>
        <span>{user.phoneSuffix ? `•• ${user.phoneSuffix}` : t('account')}</span>
      </summary>
      <div className="account-actions">
        <Link
          href="/cases"
          onClick={() => {
            if (menu.current) menu.current.open = false;
          }}
        >
          {t('myCases')}
        </Link>
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await logout();
              router.replace('/');
            } catch (e) {
              toast(e instanceof Error ? e.message : t('somethingWrong'));
            } finally {
              setBusy(false);
            }
          }}
        >
          {t('logout')}
        </button>
      </div>
    </details>
  );
}
