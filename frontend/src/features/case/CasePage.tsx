'use client';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import { ArrowRight, Volume2, ShieldCheck, Check } from 'lucide-react';
import { api, MOCK, type CaseStatus } from '@/lib/api';
import { useAuth } from '@/features/auth/useAuth';
import { useApp } from '@/components/providers';
import { EmergencyStrip, PageTop } from '@/components/layout/index';
import { Button, ErrorBox } from '@/components/ui/index';
const OtpDialog = dynamic(() => import('@/features/auth/OtpDialog').then((m) => m.OtpDialog), {
  ssr: false,
});
export function CasePage({ caseNo: initialCase }: { caseNo?: string }) {
  const t = useTranslations();
  const { lang } = useApp();
  const auth = useAuth();
  const [error, setError] = useState('');
  const [caseNo, setCaseNo] = useState(initialCase || '');
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<CaseStatus | null>(null);
  async function load() {
    const result = await api.case(caseNo.trim().toUpperCase());
    setData(result);
    setOpen(false);
  }
  function speak() {
    if (!data || !('speechSynthesis' in window)) return;
    const text = `${t('active')}. ${t('recordsChecked')}: ${data.recordsChecked}. ${data.timeline.map((x) => x.text).join('. ')}`;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  }
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main">
        <PageTop
          eyebrow={t('checkCase')}
          title={t(data ? 'caseStatus' : 'caseTitle')}
          description={data ? caseNo : t('caseDesc')}
        />
        {MOCK && <div className="demo-notice">{t('consent')}</div>}
        {error && <ErrorBox message={error} />}
        {!data ? (
          <form
            className="app-panel case-form"
            onSubmit={(e) => {
              e.preventDefault();
              setError('');
              if (auth.user)
                void load().catch((e) =>
                  setError(e instanceof Error ? e.message : t('somethingWrong')),
                );
              else setOpen(true);
            }}
          >
            <label htmlFor="case-number" className="field-label">
              {t('caseNumber')}
            </label>
            <input
              id="case-number"
              className="input uppercase"
              placeholder={t('casePlaceholder')}
              required
              value={caseNo}
              onChange={(e) => setCaseNo(e.target.value.toUpperCase())}
              autoComplete="off"
              pattern="KHJ-[0-9]{4}-[0-9]{5,}"
            />
            <Button type="submit">
              {t('openCase')}
              <ArrowRight size={16} />
            </Button>
          </form>
        ) : (
          <div className="app-panel page-enter">
            <div className="flex justify-between items-center gap-4">
              <div className="flex gap-3 items-center">
                <span className="done-icon !w-10 !h-10 !m-0">
                  <Check size={19} />
                </span>
                <div>
                  <h2 className="text-2xl">{MOCK ? t('active') : data.status}</h2>
                  <p className="text-[length:var(--type-11)] text-[var(--muted)] mt-1">
                    {t('lastChecked')}:{' '}
                    {new Date(data.lastCheckedAt).toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN')}
                  </p>
                </div>
              </div>
              <button className="icon-button" onClick={speak} aria-label={t('listenUpdate')}>
                <Volume2 size={22} />
              </button>
            </div>
            <div className="case-status-grid">
              <div className="case-stat">
                <strong>{data.recordsChecked.toLocaleString()}</strong>
                <p>{t('recordsChecked')}</p>
              </div>
              <div className="case-stat">
                <strong>{data.pendingReview}</strong>
                <p>{t('pendingReview')}</p>
              </div>
            </div>
            <ol className="timeline">
              {data.timeline.map((event, i) => (
                <li key={i}>
                  <p>{event.text}</p>
                  <time>
                    {new Date(event.at).toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN')}
                  </time>
                </li>
              ))}
            </ol>
            <Button variant="outline" onClick={speak}>
              <Volume2 size={17} />
              {t('listenUpdate')}
            </Button>
            <p className="record-privacy">
              <ShieldCheck size={15} />
              {t('matchNote')}
            </p>
          </div>
        )}
        <OtpDialog open={open} onOpenChange={setOpen} onVerified={load} />
      </main>
    </>
  );
}
