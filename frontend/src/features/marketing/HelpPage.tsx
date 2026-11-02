'use client';
import { useTranslations } from 'next-intl';
import { Phone, ShieldCheck, FileText, Mic, Trash2, ArrowUpRight } from 'lucide-react';
import { del } from '@/lib/storage/idb';
import { clearSearchContexts } from '@/lib/storage/search-context';
import { useApp } from '@/components/providers';
import { Button, ActionLink } from '@/components/ui/index';
import { EmergencyStrip, PageTop } from '@/components/layout/index';
export function HelpPage() {
  const t = useTranslations();
  const { toast } = useApp();
  async function clearData() {
    for (const k of Object.keys(localStorage))
      if (k.startsWith('khoj-') && !['khoj-language', 'khoj-mode'].includes(k))
        localStorage.removeItem(k);
    for (const k of Object.keys(sessionStorage))
      if (k.startsWith('khoj-')) sessionStorage.removeItem(k);
    await Promise.all([del('khoj-draft-missing'), del('khoj-draft-found')]);
    await clearSearchContexts();
    toast(t('dataCleared'));
  }
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main">
        <PageTop eyebrow={t('navHelp')} title={t('helpTitle')} description={t('helpIntro')} />
        <div className="help-grid">
          <section className="app-panel help-emergency">
            <Phone size={26} />
            <h2>{t('helpEmergency')}</h2>
            <p>{t('helpIntro')}</p>
            <div>
              <a className="button dark" href="tel:112">
                {t('callEmergency')}
                <ArrowUpRight size={15} />
              </a>
              <a className="button outline" href="tel:1098">
                {t('callChild')}
                <ArrowUpRight size={15} />
              </a>
            </div>
          </section>
          <section className="app-panel">
            <FileText className="help-icon" size={26} />
            <h2>{t('helpReporting')}</h2>
            <p>{t('helpReportingDesc')}</p>
            <ActionLink href="/report/missing" variant="outline">
              {t('reportMissing')}
              <ArrowUpRight size={15} />
            </ActionLink>
          </section>
          <section className="app-panel">
            <Mic className="help-icon" size={26} />
            <h2>{t('helpVoice')}</h2>
            <p>{t('helpVoiceDesc')}</p>
          </section>
          <section className="app-panel">
            <ShieldCheck className="help-icon" size={26} />
            <h2>{t('principle3').replace('\n', ' ')}</h2>
            <p>{t('principle3desc')}</p>
            <ActionLink href="/search" variant="outline">
              {t('searchDesc')}
              <ArrowUpRight size={15} />
            </ActionLink>
          </section>
          <section className="app-panel" id="privacy">
            <ShieldCheck className="help-icon" size={26} />
            <h2>{t('helpPrivacy')}</h2>
            <p>{t('helpPrivacyDesc')}</p>
            <Button variant="outline" onClick={clearData}>
              <Trash2 size={15} />
              {t('clearData')}
            </Button>
          </section>
        </div>
      </main>
    </>
  );
}
