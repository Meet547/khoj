'use client';
import { useTranslations } from 'next-intl';
import { CheckCheck, Pencil, ShieldCheck } from 'lucide-react';
import type { Kind, PersonDraft } from '@/lib/api';
import { fields, fieldLabels } from './fields';
export function SummaryCard({
  draft,
  kind,
  onEdit,
}: {
  draft: PersonDraft;
  kind: Kind;
  onEdit: (field: (typeof fields)[number], value: string) => void;
}) {
  const t = useTranslations();
  const labels = { ...fieldLabels, place: kind === 'found' ? 'foundPlace' : 'place' };
  const fieldValue = (field: (typeof fields)[number]) => {
    const value = draft[field];
    return Array.isArray(value) ? value.join(', ') : value || '';
  };
  return (
    <>
      <h2 className="live-record-title">
        <CheckCheck size={20} />
        {t('understood')}
      </h2>
      <div className="record-legend">
        <span>
          <i className="legend-known" />
          {t('knownDetail')}
        </span>
        <span>
          <i className="legend-unknown" />
          {t('unknownDetail')}
        </span>
      </div>
      {fields.map((f) => (
        <div
          key={`${f}-${draft[f]}`}
          className={`record-row ${fieldValue(f) ? 'entered' : 'unknown'} ${draft.fieldConfidence[f] < 0.6 ? 'low-confidence' : ''}`}
        >
          <span>{t(labels[f])}</span>
          <button
            type="button"
            aria-label={`${t('edit')} ${t(labels[f])}: ${fieldValue(f) || t('notMentioned')}`}
            onClick={() => {
              onEdit(f, fieldValue(f));
            }}
          >
            <span>
              <strong className={!fieldValue(f) ? 'not-yet' : ''}>
                {fieldValue(f) || t('notMentioned')}
              </strong>
              {fieldValue(f) && <small className="known-label">{t('knownDetail')}</small>}
              {draft.fieldConfidence[f] < 0.6 && <small>{t('confirmField')}</small>}
            </span>
            <Pencil size={11} />
          </button>
        </div>
      ))}
      <p className="record-privacy">
        <ShieldCheck size={15} />
        {t('reviewNote')}
      </p>
    </>
  );
}
