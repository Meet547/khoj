'use client';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { OtpForm } from './OtpDialog';
import { useAuth } from './useAuth';
import { Button } from '@/components/ui';
import { EmergencyStrip } from '@/components/layout';
export function LoginPage({ next }: { next: string }) {
  const t = useTranslations(),
    router = useRouter(),
    auth = useAuth();
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main">
        <section className="app-panel auth-panel">
          <h1 className="panel-title">{t('signIn')}</h1>
          <p className="panel-desc">{t('phoneDesc')}</p>
          {auth.user ? (
            <Button onClick={() => router.replace(next)}>{t('continue')}</Button>
          ) : (
            <OtpForm
              onVerified={async () => {
                router.replace(next);
              }}
            />
          )}
        </section>
      </main>
    </>
  );
}
