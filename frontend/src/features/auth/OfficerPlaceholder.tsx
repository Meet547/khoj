'use client';
import { useTranslations } from 'next-intl';
import { RequireRole } from './guards';
export function OfficerPlaceholder() {
  const t = useTranslations();
  return (
    <main id="main" className="app-main">
      <h1 className="panel-title">{t('officerArea')}</h1>
      <RequireRole role="officer">
        <p>{t('notAvailableDemo')}</p>
      </RequireRole>
    </main>
  );
}
