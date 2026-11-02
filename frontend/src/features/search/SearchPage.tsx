'use client';
import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import {
  Search,
  LoaderCircle,
  RefreshCw,
  UserRound,
  ShieldCheck,
  Info,
  ArrowRight,
} from 'lucide-react';
import { api, MOCK, type SearchResult, type Hit } from '@/lib/api';
import { useAuth } from '@/features/auth/useAuth';
import { useApp } from '@/components/providers';
import { Button, ErrorBox } from '@/components/ui/index';
import { EmergencyStrip, PageTop } from '@/components/layout/index';
import {
  createSearchContext,
  createSamplePreviewContext,
  type SearchContext,
} from '@/features/search/demo';
import { loadSearchContext, rememberSearchContext } from '@/lib/storage/search-context';
import { extractDemoDescription } from '@/mocks/data/extract';
const AgentSearch = dynamic(
  () => import('@/features/search/AgentSearch').then((m) => m.AgentSearch),
  {
    ssr: false,
  },
);
const OtpDialog = dynamic(() => import('@/features/auth/OtpDialog').then((m) => m.OtpDialog), {
  ssr: false,
});
const VoiceOrb = dynamic(() => import('@/features/voice/VoiceOrb').then((m) => m.VoiceOrb), {
  ssr: false,
});
const states = [
  'CHANDIGARH',
  'DELHI',
  'HARYANA',
  'HIMACHAL PRADESH',
  'PUNJAB',
  'RAJASTHAN',
  'UTTAR PRADESH',
  'UTTARAKHAND',
];
function MatchCard({ hit }: { hit: Hit }) {
  const t = useTranslations();
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <article className="match-card">
      <div className="match-photo">
        {hit.record.imageUrl && !imageFailed ? (
          <img
            src={hit.record.imageUrl}
            alt={t('person')}
            onError={() => setImageFailed(true)}
            className="w-full h-full object-cover rounded-xl"
          />
        ) : (
          <>
            <UserRound size={34} />
            <small>{t('noPhoto')}</small>
          </>
        )}
      </div>
      <div className="match-content">
        <div className="match-top">
          <span className={`band-chip ${hit.band.toLowerCase()}`}>{t(hit.band.toLowerCase())}</span>
          <span className="record-source">
            {t('source')} · {hit.record.state}
          </span>
        </div>
        <h3>{hit.record.placeOfMissing}</h3>
        <p className="match-details">
          {hit.record.policeStation} · {hit.record.district}
          <br />
          {hit.record.details.age} · {hit.record.status} · {hit.record.ddDate}
        </p>
        <ul className="match-reasons">
          {hit.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
        {hit.band === 'Strong' && <p className="match-review-note">{t('matchNote')}</p>}
      </div>
    </article>
  );
}
export function SearchPage() {
  const [ready, setReady] = useState(false);
  const [context, setContext] = useState<SearchContext | null>(null);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === '1') {
      setContext(createSamplePreviewContext());
      setReady(true);
      return;
    }
    if (params.has('new')) {
      setReady(true);
      return;
    }
    void loadSearchContext(params.get('case') || undefined)
      .then((c) => {
        if (active) {
          setContext(c);
          setReady(true);
        }
      })
      .catch(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);
  if (!ready)
    return (
      <>
        <EmergencyStrip />
        <main id="main" className="app-main">
          <div className="loading-spinner" role="status">
            <LoaderCircle className="spinner" size={24} />
            <span className="sr-only">Loading saved search</span>
          </div>
        </main>
      </>
    );
  if (context && (MOCK || context.demoOnly))
    return (
      <AgentSearch
        key={context.id}
        context={context}
        onStartNew={() => {
          setContext(null);
          window.history.replaceState(null, '', '/search?new=1');
        }}
      />
    );
  return (
    <SearchForm
      initialContext={context}
      onDemoReady={(c) => {
        setContext(c);
        window.scrollTo({ top: 0, behavior: 'instant' });
        document.querySelector('.page-scroll')?.scrollTo({ top: 0, behavior: 'instant' });
      }}
    />
  );
}
function SearchForm({
  onDemoReady,
  initialContext,
}: {
  onDemoReady: (context: SearchContext) => void;
  initialContext?: SearchContext | null;
}) {
  const t = useTranslations();
  const { lang, toast, mode, setMode } = useApp();
  const auth = useAuth();
  const [state, setState] = useState(initialContext?.state || '');
  const [district, setDistrict] = useState(initialContext?.district || '');
  const [status, setStatus] = useState('Untraced');
  const [gender, setGender] = useState(initialContext?.draft.gender || '');
  const [query, setQuery] = useState(initialContext?.description || '');
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState('');
  const [otpOpen, setOtpOpen] = useState(false);
  const voice = mode === 'voice';
  const controller = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [busy]);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (initialContext) return;
    try {
      const saved = sessionStorage.getItem('khoj-last-query');
      if (saved) {
        const d = JSON.parse(saved);
        setQuery(d.query || '');
        setState(d.state || '');
        setDistrict(d.district || '');
      }
    } catch {}
  }, []);
  async function search(refresh = false) {
    if (MOCK) {
      const extracted = extractDemoDescription(query);
      const context = createSearchContext(
        query,
        {
          kind: 'missing',
          ...extracted,
          gender: extracted.gender || gender || undefined,
          place: extracted.place || district || state || undefined,
        },
        { verified: Boolean(auth.user), source: 'search', state, district },
      );
      await rememberSearchContext(context).catch(() => {});
      onDemoReady(context);
      return;
    }
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setElapsed(0);
    setError('');
    setResult(null);
    sessionStorage.setItem('khoj-last-query', JSON.stringify({ query, state, district }));
    try {
      const r = await api.search(query, { state, district, status, gender }, c.signal, refresh);
      setResult(r);
      setTimeout(
        () => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
        50,
      );
    } catch (e) {
      if (e instanceof Error && e.name !== 'AbortError') setError(e.message);
    } finally {
      if (controller.current === c) setBusy(false);
    }
  }
  async function saveSearch() {
    if (!MOCK)
      throw new Error(
        lang === 'hi'
          ? 'स्वचालित खोज सहेजने के लिए बैकएंड एंडपॉइंट उपलब्ध नहीं है।'
          : 'The backend does not yet provide a saved-search endpoint.',
      );
    const saved = JSON.parse(localStorage.getItem('khoj-saved-searches') || '[]');
    saved.push({
      query,
      filters: { state, district, status, gender },
      at: new Date().toISOString(),
    });
    localStorage.setItem('khoj-saved-searches', JSON.stringify(saved));
    setOtpOpen(false);
    toast(t('savedSearch'));
  }
  async function audioSearch(audio: Blob) {
    const s = await api.session(lang, 'missing');
    const r = await api.turn(s.sessionId, { audio });
    setQuery(r.transcript);
    setMode('text');
  }
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="app-main">
        <PageTop
          eyebrow={t('searchDesc')}
          title={t('searchTitle')}
          description={t('searchIntro')}
        />
        {MOCK && <div className="demo-notice">{t('faq5a')}</div>}
        <form
          className="app-panel"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <div className="search-form-grid">
            <div>
              <label className="field-label" htmlFor="search-state">
                {t('state')} *
              </label>
              <select
                className="select"
                id="search-state"
                required
                value={state}
                disabled={busy}
                onChange={(e) => setState(e.target.value)}
              >
                <option value="">{t('selectState')}</option>
                {states.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="search-district">
                {t('district')}
              </label>
              <input
                className="input"
                id="search-district"
                placeholder={t('districtPlaceholder')}
                value={district}
                disabled={busy}
                onChange={(e) => setDistrict(e.target.value)}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="search-status">
                {t('status')}
              </label>
              <select
                className="select"
                id="search-status"
                value={status}
                disabled={busy}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="Untraced">{t('untraced')}</option>
                <option value="Traced">{t('traced')}</option>
                <option value="Any">{t('any')}</option>
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="search-gender">
                {t('gender')}
              </label>
              <select
                className="select"
                id="search-gender"
                value={gender}
                disabled={busy}
                onChange={(e) => setGender(e.target.value)}
              >
                <option value="">{t('any')}</option>
                <option value="Male">{t('male')}</option>
                <option value="Female">{t('female')}</option>
                <option value="Other">{t('other')}</option>
              </select>
            </div>
          </div>
          <div className="search-description">
            <div className="search-description-label">
              <label className="field-label" htmlFor="search-query">
                {t('description')} *
              </label>
            </div>
            {voice && <VoiceOrb question={t('description')} onAudio={audioSearch} />}
            <textarea
              className="textarea"
              id="search-query"
              placeholder={t('searchPlaceholder')}
              required
              value={query}
              disabled={busy}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="search-submit">
            <small>
              <ShieldCheck size={13} className="inline mr-1" />
              {t('matchNote')}
            </small>
            <Button disabled={busy} type="submit">
              {busy ? <LoaderCircle className="spinner" size={17} /> : <Search size={17} />}{' '}
              {t('searchButton')}
            </Button>
          </div>
        </form>
        {busy && (
          <section className="search-progress" role="status" aria-live="polite">
            <div className="search-progress-heading">
              <LoaderCircle size={22} className="spinner" />
              <div>
                <p>{t(MOCK ? 'demoWait' : 'searchWait')}</p>
                <small>{t('elapsed', { seconds: elapsed })}</small>
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  controller.current?.abort();
                  setBusy(false);
                }}
              >
                {t('cancel')}
              </Button>
            </div>
            {[1, 2, 3].map((n) => (
              <div className="skeleton-card" key={n} aria-hidden="true">
                <div className="skeleton-image" />
                <div className="skeleton-lines">
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            ))}
          </section>
        )}
        {error && (
          <>
            <ErrorBox message={error} />
            <Button variant="outline" onClick={() => void search()}>
              {t('retry')}
              <RefreshCw size={15} />
            </Button>
          </>
        )}
        <div ref={resultRef} className="scroll-mt-8">
          {result && (
            <>
              <div className="results-header">
                <div>
                  <h2>
                    {t('resultsMeta', { count: result.hits.length, scanned: result.scanned })}
                  </h2>
                  <p>
                    {MOCK
                      ? t('checkedNow')
                      : new Date(result.checkedAt).toLocaleString(
                          lang === 'hi' ? 'hi-IN' : 'en-IN',
                        )}{' '}
                    · {result.source}
                  </p>
                </div>
                <Button variant="outline" onClick={() => void search(true)}>
                  <RefreshCw size={14} />
                  {t('checkAgain')}
                </Button>
              </div>
              {result.note && (
                <div className="info-box">
                  <Info size={17} />
                  {result.note}
                </div>
              )}
              {result.hits.length ? (
                result.hits.map((hit, i) => <MatchCard key={i} hit={hit} />)
              ) : (
                <div className="empty-state">
                  <Search size={36} />
                  <h2>{t('noResults')}</h2>
                  <p>{t('noResultsDesc')}</p>
                  <Button onClick={() => setOtpOpen(true)}>
                    {t('keepChecking')}
                    <ArrowRight size={16} />
                  </Button>
                </div>
              )}
              <p className="disclaimer">{result.disclaimer}</p>
              {result.hits.length > 0 && (
                <div className="text-center mt-5">
                  <Button variant="outline" onClick={() => setOtpOpen(true)}>
                    {t('keepChecking')}
                    <ArrowRight size={16} />
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
        <OtpDialog open={otpOpen} onOpenChange={setOtpOpen} onVerified={saveSearch} />
      </main>
    </>
  );
}
