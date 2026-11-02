'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import type { z } from 'zod';
import { casesSchema } from '@/lib/api/types';
import { useRequireAuth } from '@/features/auth/guards';
import { Button, ErrorBox, ActionLink } from '@/components/ui';
import { EmergencyStrip } from '@/components/layout';
export function MyCases() {
  const t = useTranslations(),
    auth = useRequireAuth(),
    [data, setData] = useState<z.infer<typeof casesSchema> | null>(null),
    [error, setError] = useState(''),
    [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!auth.user) return;
    let active = true;
    setError('');
    void api
      .cases()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : t('somethingWrong'));
      });
    return () => {
      active = false;
    };
  }, [auth.user, attempt, t]);
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main">
        <h1 className="panel-title">{t('myCases')}</h1>
        {auth.status === 'error' ? (
          <>
            <ErrorBox message={auth.error} />
            <Button onClick={() => void auth.refresh()}>{t('retry')}</Button>
          </>
        ) : !auth.user || (!data && !error) ? (
          <p role="status">{t('loading')}</p>
        ) : error ? (
          <>
            <ErrorBox message={error} />
            <Button onClick={() => setAttempt((value) => value + 1)}>{t('retry')}</Button>
          </>
        ) : (
          <div className="case-list">
            {data?.cases.length ? (
              data.cases.map((item) => (
                <Link
                  className="case-list-card"
                  href={`/case/${encodeURIComponent(item.caseNo)}`}
                  key={item.caseNo}
                >
                  <strong>{item.caseNo}</strong>
                  <span className="band-chip">{t('active')}</span>
                  <span>
                    {t('lastChecked')}:{' '}
                    {new Intl.DateTimeFormat(undefined, {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                      timeZone: 'Asia/Kolkata',
                    }).format(new Date(item.lastCheckedAt))}
                  </span>
                </Link>
              ))
            ) : (
              <section className="app-panel">
                <p>{t('noCases')}</p>
                <ActionLink href="/report/missing">{t('reportMissing')}</ActionLink>
              </section>
            )}
          </div>
        )}
      </main>
    </>
  );
}
