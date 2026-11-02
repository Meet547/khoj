'use client';
import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { get, set, del } from '@/lib/storage/idb';
import { useTranslations } from 'next-intl';
import {
  ArrowRight,
  Check,
  Copy,
  Share2,
  LoaderCircle,
  ShieldCheck,
  Volume2,
  Info,
  Mic,
} from 'lucide-react';
import { api, MOCK, type Kind, type PersonDraft } from '@/lib/api';
import { useApp } from '@/components/providers';
import { Button, ActionLink, Modal, ErrorBox } from '@/components/ui/index';
import { EmergencyStrip, SafetyBanner } from '@/components/layout/index';
import { createSearchContext, type SearchContext } from '@/features/search/demo';
import { rememberSearchContext } from '@/lib/storage/search-context';
const AgentSearch = dynamic(
  () => import('@/features/search/AgentSearch').then((m) => m.AgentSearch),
  {
    ssr: false,
  },
);
const VoiceOrb = dynamic(() => import('@/features/voice/VoiceOrb').then((m) => m.VoiceOrb), {
  ssr: false,
});
const PhotoCapture = dynamic(
  () => import('@/features/intake/PhotoCapture').then((m) => m.PhotoCapture),
  {
    ssr: false,
  },
);
const OtpForm = dynamic(() => import('@/features/auth/OtpDialog').then((m) => m.OtpForm), {
  ssr: false,
});
import type { IntakeStep as Step } from './machine';
import { fields, fieldLabels as baseLabels } from './fields';
import { useAuth } from '@/features/auth/useAuth';
import { SummaryCard } from './SummaryCard';
interface SavedDraft {
  sessionId: string;
  draft: PersonDraft;
  index: number;
  step: Step;
  question: string;
  files: File[];
  input: string;
  version?: number;
}
export function Report({ kind }: { kind: Kind }) {
  const labels = { ...baseLabels, place: kind === 'found' ? 'foundPlace' : 'place' };
  const t = useTranslations();
  const router = useRouter();
  const auth = useAuth();
  const { lang, mode, setMode, toast } = useApp();
  const [step, setStep] = useState<Step>(kind === 'found' ? 'photo' : 'describe');
  const [sessionId, setSessionId] = useState('');
  const [draft, setDraft] = useState<PersonDraft>({ kind, fieldConfidence: {} });
  const [index, setIndex] = useState(0);
  const [question, setQuestion] = useState('');
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [saved, setSaved] = useState<SavedDraft | null>(null);
  const [caseNo, setCaseNo] = useState('');
  const [matchContext, setMatchContext] = useState<SearchContext | null>(null);
  const [editField, setEditField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [replyAudio, setReplyAudio] = useState<string>();
  const initial = useRef(false);
  useEffect(() => {
    if (!ready) return;
    window.scrollTo({ top: 0, behavior: 'instant' });
    document.querySelector('.page-scroll')?.scrollTo({ top: 0, behavior: 'instant' });
  }, [step, ready]);
  const key = `khoj-draft-${kind}`;
  async function start() {
    setError('');
    try {
      const s = await api.session(lang, kind);
      setSessionId(s.sessionId);
      setReady(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
    }
  }
  useEffect(() => {
    if (initial.current) return;
    initial.current = true;
    void get<SavedDraft>(key)
      .then((d) => {
        if (d && d.step !== 'done') {
          setSaved(d);
        } else void start();
      })
      .catch(() => void start());
  }, []);
  useEffect(() => {
    if (!ready || !sessionId || step === 'done') return;
    void set(key, {
      sessionId,
      draft,
      index,
      step,
      question,
      files,
      input,
      version: 2,
    } satisfies SavedDraft).catch(() => {});
  }, [draft, index, step, sessionId, ready, question, files, input, key]);
  async function resume() {
    if (!saved) return;
    setDraft(saved.draft);
    setIndex(saved.index);
    setStep(saved.step);
    setQuestion(saved.question);
    setInput(saved.input || '');
    setFiles(saved.files || []);
    setSessionId(saved.sessionId);
    await api.restore(saved.sessionId, saved.draft, saved.index, lang, saved.step === 'save');
    setSaved(null);
    setReady(true);
  }
  async function send(text?: string, audio?: Blob) {
    setError('');
    setBusy(true);
    try {
      const r = await api.turn(sessionId, { text, audio });
      setDraft(r.draft);
      setQuestion(r.replyText);
      setReplyAudio(r.replyAudioUrl || undefined);
      setIndex(1);
      if (text || r.transcript) setInput(text || r.transcript);
      if (r.stage === 'readback') setStep(kind === 'missing' ? 'photo' : 'check');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
      if (audio) throw e;
    } finally {
      setBusy(false);
    }
  }
  async function photosDone() {
    setBusy(true);
    setError('');
    try {
      if (files.length) await api.photos(sessionId, files);
      setStep(kind === 'found' && index < 1 ? 'describe' : 'check');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
    } finally {
      setBusy(false);
    }
  }
  async function confirm() {
    setBusy(true);
    setError('');
    try {
      const result = await api.turn(sessionId, { text: t('yesCorrect') });
      if (result.stage !== 'confirmed') throw new Error(result.replyText || t('reviewTitle'));
      setStep('save');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
    } finally {
      setBusy(false);
    }
  }
  async function saveReport() {
    setBusy(true);
    setError('');
    try {
      const result = await api.confirm(sessionId);
      setCaseNo(result.caseNo);
      let contextSaved = false;
      if (kind === 'missing') {
        const description =
          input.trim() ||
          Object.entries(draft)
            .filter(([k, v]) => k !== 'fieldConfidence' && k !== 'kind' && typeof v === 'string')
            .map(([k, v]) => `${k}: ${v}`)
            .join('. ');
        const context = createSearchContext(description, draft, {
          caseNo: result.caseNo,
          verified: true,
          source: 'report',
        });
        setMatchContext(context);
        await rememberSearchContext(context)
          .then(() => {
            contextSaved = true;
          })
          .catch(() => {});
      }
      await del(key).catch(() => {});
      setStep('done');
      window.scrollTo({ top: 0, behavior: 'instant' });
      document.querySelector('.page-scroll')?.scrollTo({ top: 0, behavior: 'instant' });
      if (kind === 'missing' && MOCK && contextSaved)
        router.replace(`/search?case=${encodeURIComponent(result.caseNo)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
      throw e;
    } finally {
      setBusy(false);
    }
  }
  async function edit() {
    if (!editField) return;
    setBusy(true);
    setError('');
    try {
      const r = await api.turn(sessionId, {
        text: `Update ${editField}: ${editValue}`,
      });
      setDraft(r.draft);
      setEditField(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('somethingWrong'));
    } finally {
      setBusy(false);
    }
  }
  const active = step === 'describe' ? 0 : step === 'photo' ? 1 : step === 'check' ? 2 : 3;
  useEffect(() => {
    if (MOCK && ready && sessionId) {
      void api.restore(sessionId, draft, index, lang, step === 'save');
      setQuestion('');
    }
  }, [lang, ready, sessionId]);
  const questionText = t(
    kind === 'found' ? 'describeEverythingFound' : 'describeEverythingMissing',
  );
  const fieldValue = (f: (typeof fields)[number]) => {
    const value = draft[f];
    return Array.isArray(value) ? value.join(', ') : value || '';
  };
  const record = fields
    .map((f) => (draft[f] ? `${t(labels[f])}: ${fieldValue(f)}` : ''))
    .filter(Boolean)
    .join('; ');
  useEffect(() => {
    if (step !== 'check' || mode !== 'voice' || !('speechSynthesis' in window)) return;
    const utterance = new SpeechSynthesisUtterance(t('readback', { record }));
    utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
    return () => speechSynthesis.cancel();
  }, [step, mode, lang]);
  const recordCard = (
    <SummaryCard
      draft={draft}
      kind={kind}
      onEdit={(field, value) => {
        setEditField(field);
        setEditValue(value);
      }}
    />
  );
  if (step === 'done' && kind === 'missing' && MOCK && matchContext)
    return <AgentSearch context={matchContext} />;
  if (step === 'done')
    return (
      <>
        <EmergencyStrip />
        <main id="main" className="app-main report-main">
          <div className="app-panel done-panel page-enter">
            <div className="done-icon">
              <Check size={30} />
            </div>
            <h1>{t('doneTitle')}</h1>
            <div className="case-badge">
              <span>{t('caseNumber')}</span>
              <strong>{caseNo}</strong>
              <div className="case-badge-actions">
                <button
                  onClick={() =>
                    void navigator.clipboard
                      .writeText(caseNo)
                      .then(() => toast(t('copied')))
                      .catch(() => toast(caseNo))
                  }
                >
                  <Copy size={14} />
                  {t('copy')}
                </button>
                <button
                  onClick={() => {
                    if (navigator.share)
                      void navigator
                        .share({ title: 'KHOJ demo case', text: caseNo })
                        .catch(() => {});
                    else void navigator.clipboard.writeText(caseNo).then(() => toast(t('copied')));
                  }}
                >
                  <Share2 size={14} />
                  {t('share')}
                </button>
              </div>
            </div>
            <p>{t(kind === 'found' ? 'foundDone' : 'doneDesc')}</p>
            <div className="form-actions">
              {kind === 'missing' && (
                <ActionLink href={`/search?case=${encodeURIComponent(caseNo)}`}>
                  {t('possibleMatches')}
                  <ArrowRight size={16} />
                </ActionLink>
              )}
              <ActionLink variant="outline" href="/">
                {t('home')}
              </ActionLink>
            </div>
          </div>
        </main>
      </>
    );
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main report-main">
        <p className="report-independent">{t('independent')}</p>
        {kind === 'found' && <SafetyBanner />}
        <ol className="step-progress">
          {(kind === 'found'
            ? ['photo', 'describe', 'check', 'save']
            : ['describe', 'photo', 'check', 'save']
          ).map((s, i) => {
            const activeIdx =
              kind === 'found' ? (step === 'photo' ? 0 : step === 'describe' ? 1 : active) : active;
            return (
              <li
                key={s}
                className={i === activeIdx ? 'active' : i < activeIdx ? 'complete' : ''}
                aria-current={i === activeIdx ? 'step' : undefined}
              >
                <span className="step-number">{i < activeIdx ? <Check size={13} /> : i + 1}</span>
                {t(s)}
              </li>
            );
          })}
        </ol>
        {error && <ErrorBox message={error} />}
        {!ready && error && (
          <Button variant="outline" onClick={start}>
            {t('retry')}
          </Button>
        )}
        <div key={step} className="page-enter">
          {step === 'describe' && (
            <div className="intake-grid">
              <section className="app-panel">
                <span className="question-label">{t('oneReply')}</span>
                <h1 className="question-title" aria-live="polite">
                  {questionText}
                </h1>
                <p className="intake-hint">
                  {t(kind === 'found' ? 'wholeDescriptionHintFound' : 'wholeDescriptionHint')}
                </p>
                {mode === 'voice' ? (
                  <div className="voice-intake">
                    <VoiceOrb
                      question={questionText}
                      onAudio={async (audio) => {
                        const result = await api.turn(sessionId, { audio });
                        setInput((previous) =>
                          [previous, result.transcript].filter(Boolean).join(' '),
                        );
                      }}
                      busy={busy || !ready}
                      replyAudioUrl={replyAudio}
                    />
                    <p className="intake-hint">{t('voiceClipHelp')}</p>
                    <label className="field-label" htmlFor="live-transcript">
                      {t('transcript')}
                    </label>
                    <textarea
                      id="live-transcript"
                      className="textarea"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                    />
                    <Button
                      onClick={() => void send(input)}
                      disabled={!ready || busy || !input.trim()}
                    >
                      {t('send')}
                      <ArrowRight size={17} />
                    </Button>
                  </div>
                ) : (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void send(input);
                    }}
                  >
                    <label htmlFor="answer" className="sr-only">
                      {questionText}
                    </label>
                    <div className="description-input">
                      <textarea
                        id="answer"
                        className="textarea report-long-answer"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={t('wholeDescriptionPlaceholder')}
                        disabled={busy}
                        required
                      />
                      <button
                        type="button"
                        className="input-mic icon-button"
                        aria-label={t('speakInstead')}
                        onClick={() => setMode('voice')}
                      >
                        <Mic size={20} />
                      </button>
                    </div>
                    <div className="form-actions">
                      <Button type="submit" disabled={!ready || busy || !input.trim()}>
                        {busy ? (
                          <LoaderCircle className="spinner" size={17} />
                        ) : (
                          <ArrowRight size={17} />
                        )}{' '}
                        {t(busy ? 'processing' : 'send')}
                      </Button>
                    </div>
                  </form>
                )}
                <p className="extraction-demo-note">
                  {t(MOCK ? 'demoExtraction' : 'extractionHelp')}
                </p>
              </section>
              <aside className="app-panel">{recordCard}</aside>
            </div>
          )}
          {step === 'photo' && (
            <section className="app-panel photo-panel">
              <h1 className="panel-title">{t('photoTitle')}</h1>
              <p className="panel-desc">{t(kind === 'found' ? 'foundPhotoDesc' : 'photoDesc')}</p>
              <PhotoCapture files={files} onChange={setFiles} max={kind === 'found' ? 3 : 1} />
              <div className="form-actions">
                <Button onClick={photosDone} disabled={busy}>
                  {busy ? <LoaderCircle size={17} className="spinner" /> : <ArrowRight size={17} />}{' '}
                  {t('continue')}
                </Button>
                {!files.length && (
                  <button className="skip-button" disabled={busy} onClick={photosDone}>
                    {t('skip')}
                  </button>
                )}
              </div>
            </section>
          )}
          {step === 'check' && (
            <section className="app-panel review-panel">
              <h1 className="panel-title">{t('reviewTitle')}</h1>
              <div className="readback">
                {t('readback', { record: record || t('noExtractedDetails') })}
                <button
                  className="icon-button"
                  aria-label={t('listenUpdate')}
                  onClick={() => {
                    if (!('speechSynthesis' in window)) return;
                    const u = new SpeechSynthesisUtterance(t('readback', { record }));
                    u.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
                    speechSynthesis.cancel();
                    speechSynthesis.speak(u);
                  }}
                >
                  <Volume2 size={20} />
                </button>
              </div>
              {recordCard}
              {Object.values(draft.fieldConfidence).some((v) => v < 0.6) && (
                <div className="info-box mt-5">
                  <Info size={16} />
                  {t('confirmLow')}
                </div>
              )}
              <div className="form-actions">
                <Button onClick={confirm} disabled={busy}>
                  {busy ? <LoaderCircle size={17} className="spinner" /> : <Check size={17} />}{' '}
                  {t('yesCorrect')}
                </Button>
                <Button variant="outline" onClick={() => setStep('describe')}>
                  {t('changeDescription')}
                </Button>
              </div>
            </section>
          )}
          {step === 'save' && (
            <section className="app-panel photo-panel">
              <h1 className="panel-title">{t('saveTitle')}</h1>
              <p className="panel-desc">{t('phoneDesc')}</p>
              {auth.status === 'loading' ? (
                <p role="status">{t('loading')}</p>
              ) : auth.status === 'error' ? (
                <>
                  <ErrorBox message={auth.error} />
                  <Button onClick={() => void auth.refresh()}>{t('retry')}</Button>
                </>
              ) : auth.user ? (
                <Button onClick={() => void saveReport().catch(() => {})} disabled={busy}>
                  {busy ? <LoaderCircle className="spinner" size={18} /> : <Check size={18} />}{' '}
                  {t('saveReport')}
                </Button>
              ) : (
                <OtpForm onVerified={saveReport} />
              )}
              <p className="record-privacy mt-5">
                <ShieldCheck size={16} />
                {t('consent')}
              </p>
            </section>
          )}
        </div>
        <Modal
          open={!!saved}
          hideClose
          onOpenChange={() => {}}
          title={t('draftTitle')}
          description={t('draftDesc')}
        >
          <div className="form-actions">
            <Button onClick={resume}>
              {t('continue')}
              <ArrowRight size={16} />
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void del(key);
                setSaved(null);
                void start();
              }}
            >
              {t('startAgain')}
            </Button>
          </div>
        </Modal>
        <Modal
          open={!!editField}
          onOpenChange={(v) => {
            if (!v) setEditField(null);
          }}
          title={`${t('edit')} ${editField ? t(labels[editField as keyof typeof labels]) : ''}`}
        >
          <form
            className="edit-field-form"
            onSubmit={(e) => {
              e.preventDefault();
              void edit();
            }}
          >
            <input
              className="input"
              value={editValue}
              aria-label={t('edit')}
              onChange={(e) => setEditValue(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy}>
              {t('saveChanges')}
              <Check size={16} />
            </Button>
          </form>
        </Modal>
      </main>
    </>
  );
}
