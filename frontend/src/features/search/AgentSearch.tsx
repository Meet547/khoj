'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Copy,
  Database,
  FileCheck2,
  Info,
  LoaderCircle,
  MapPin,
  Route,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Users,
  RotateCcw,
  ImageOff,
} from 'lucide-react';
import {
  AGENT_PHASES,
  DEMO_DONE_MS,
  REVEAL_INTERVAL_MS,
  buildSampleMatches,
  demoProgress,
  type SearchContext,
  type SampleMatch,
} from '@/features/search/demo';
import { rememberSearchContext } from '@/lib/storage/search-context';
import { useApp } from '@/components/providers';
import { ActionLink, Button } from '@/components/ui/index';
import { EmergencyStrip } from '@/components/layout/index';
const icons = [Route, Database, ScanSearch, ShieldCheck];
function SamplePhoto({ match, view }: { match: SampleMatch; view: 0 | 1 }) {
  const [failed, setFailed] = useState(false);
  const col = (match.female ? 2 : 0) + view;
  return (
    <div
      className="sample-photo"
      role="img"
      aria-label={`Synthetic sample portrait ${view + 1} for ${match.id}`}
    >
      <span className="synthetic-watermark">AI · SAMPLE</span>
      {failed ? (
        <ImageOff size={28} />
      ) : (
        <svg
          viewBox="0 0 362 362"
          width="362"
          height="362"
          aria-hidden="true"
          focusable="false"
          overflow="hidden"
        >
          <image
            href={`/sample-people/${match.cohort}.webp`}
            x={-col * 362}
            y={-match.row * 362}
            width="1448"
            height="1086"
            onError={() => setFailed(true)}
          />
        </svg>
      )}
    </div>
  );
}
function ResultCard({ match, index }: { match: SampleMatch; index: number }) {
  const t = useTranslations();
  const [details, setDetails] = useState(index === 0);
  const band =
    match.confidence === null
      ? 'listed'
      : match.confidence >= 80
        ? 'strong'
        : match.confidence >= 55
          ? 'possible'
          : 'weak';
  const topReasons = match.comparisons
    .filter((c) => c.score !== null && c.score >= 0.65)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 3);
  return (
    <article className="agent-match-card page-enter">
      <div className="agent-match-top">
        <div className="match-rank">
          <span>0{index + 1}</span>
          <div>
            <p className="match-ref">{match.id}</p>
            <h3>{t('sampleRecordTitle', { index: index + 1 })}</h3>
          </div>
        </div>
        <div className={`illustrative-confidence ${band}`}>
          <strong>{t(band)}</strong>
          <span>{t('demoConfidence')}</span>
        </div>
      </div>
      <div className="agent-match-grid">
        <div className="sample-gallery">
          <div className="sample-photo-pair">
            <SamplePhoto match={match} view={0} />
            <SamplePhoto match={match} view={1} />
          </div>
          <div className="sample-photo-captions">
            <span>{t('frontView')}</span>
            <span>{t('secondView')}</span>
          </div>
          <p>{t('syntheticPhotoNote')}</p>
        </div>
        <div className="candidate-details">
          <div className="candidate-badges">
            <span className={`band-chip ${band}`}>{t(band)}</span>
            <span className="sample-only-chip">{t('fictionalRecord')}</span>
          </div>
          <p className="candidate-description">{match.description}</p>
          <dl className="candidate-location">
            <div>
              <dt>
                <MapPin size={14} />
                {t('recordLocation')}
              </dt>
              <dd>{match.city}</dd>
            </div>
            <div>
              <dt>
                <Clock size={14} />
                {t('lastSeenLocation')}
              </dt>
              <dd>
                {match.lastSeen}
                <small>{match.lastSeenAt}</small>
              </dd>
            </div>
            <div>
              <dt>
                <FileCheck2 size={14} />
                {t('recordSource')}
              </dt>
              <dd>
                {match.station}
                <small>{t('sampleDataset')}</small>
              </dd>
            </div>
          </dl>
          <div className="candidate-reasons">
            {topReasons.length ? (
              topReasons.map((c) => (
                <span key={c.key}>
                  <Check size={12} />
                  {t(`reason_${c.key}`)}
                </span>
              ))
            ) : (
              <span>
                <Info size={12} />
                {t('limitedSimilarity')}
              </span>
            )}
          </div>
        </div>
      </div>
      <button
        className="comparison-toggle"
        aria-expanded={details}
        onClick={() => setDetails(!details)}
      >
        {t('viewComparison')}
        {details ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {details && (
        <div className="comparison-panel">
          <div className="comparison-column-labels">
            <span>{t('comparedDetail')}</span>
            <span>{t('yourReport')}</span>
            <span>{t('sampleRecord')}</span>
            <span>{t('similarity')}</span>
          </div>
          {match.comparisons.map((c) => (
            <div className="comparison-row" key={c.key}>
              <strong>{t(`compare_${c.key}`)}</strong>
              <span>{c.query || t('notMentioned')}</span>
              <span>{c.record}</span>
              <div className="comparison-metric">
                {c.score === null ? (
                  <small>{t('notCompared')}</small>
                ) : (
                  <>
                    <strong>
                      {t(c.score >= 0.8 ? 'strong' : c.score >= 0.55 ? 'possible' : 'weak')}
                    </strong>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="agent-match-review">
        <ShieldCheck size={15} />
        {t('matchNote')}
      </div>
    </article>
  );
}
export function AgentSearch({
  context,
  onStartNew,
}: {
  context: SearchContext;
  onStartNew?: () => void;
}) {
  const t = useTranslations();
  const { toast } = useApp();
  const [startedAt, setStartedAt] = useState(context.startedAt);
  const [elapsed, setElapsed] = useState(() =>
    Math.max(0, Date.now() - Date.parse(context.startedAt)),
  );
  const [showActivity, setShowActivity] = useState(true);
  const [showBrief, setShowBrief] = useState(false);
  const [manualReveal, setManualReveal] = useState(false);
  const matches = useMemo(
    () => buildSampleMatches(context.draft, context.description),
    [context.draft, context.description],
  );
  const progress = demoProgress(elapsed);
  const done = progress.done;
  const revealed = manualReveal ? 3 : progress.revealed;
  const completionAnnounced = useRef(false);
  useEffect(() => {
    const tick = () => setElapsed(Math.max(0, Date.now() - Date.parse(startedAt)));
    tick();
    const id = setInterval(() => {
      tick();
      if (Date.now() - Date.parse(startedAt) >= DEMO_DONE_MS + 3 * REVEAL_INTERVAL_MS)
        clearInterval(id);
    }, 250);
    return () => clearInterval(id);
  }, [startedAt]);
  useEffect(() => {
    if (elapsed >= DEMO_DONE_MS + 3 * REVEAL_INTERVAL_MS && !completionAnnounced.current) {
      completionAnnounced.current = true;
      setShowActivity(false);
    }
  }, [elapsed]);
  useEffect(() => {
    document.title = `${done ? t('agentDoneTitle') : t('agentWorkingTitle')} · KHOJ`;
  }, [done, t]);
  async function replay() {
    const next = new Date().toISOString();
    setStartedAt(next);
    setElapsed(0);
    setManualReveal(false);
    setShowActivity(true);
    completionAnnounced.current = false;
    if (!context.demoOnly)
      await rememberSearchContext({ ...context, startedAt: next }).catch(() => {});
  }
  return (
    <>
      <EmergencyStrip />
      <main id="main" className="agent-search-page">
        <div className="agent-page-heading">
          <div>
            <p className="eyebrow">{t('searchRoom')}</p>
            <h1>{t(done ? 'agentDoneTitle' : 'agentWorkingTitle')}</h1>
            <p>{t(context.demoOnly ? 'sampleBriefIntro' : 'descriptionCarried')}</p>
          </div>
          <div className={`agent-global-status ${done ? 'complete' : ''}`}>
            {done ? <Check size={16} /> : <LoaderCircle size={16} className="spinner" />}
            {t(done ? 'demoComplete' : 'demoRunning')}
          </div>
        </div>
        <div className="agent-demo-disclaimer">
          <Info size={16} />
          <p>{t('agentSimulationNotice')}</p>
          <span>DEMO</span>
        </div>
        <section className="search-brief">
          <div className="brief-heading">
            <span className="brief-check">
              <FileCheck2 size={20} />
            </span>
            <div>
              <h2>
                {t(
                  context.demoOnly
                    ? 'sampleBriefTitle'
                    : context.verified
                      ? 'verifiedBrief'
                      : 'savedBrief',
                )}
              </h2>
              <p>
                {context.caseNo || context.id}
                {context.verified && <> · {t('phoneVerified')}</>}
              </p>
            </div>
            <button
              className="icon-button"
              aria-label={t('copy')}
              onClick={() =>
                void navigator.clipboard
                  .writeText(context.caseNo || context.id)
                  .then(() => toast(t('copied')))
                  .catch(() => {})
              }
            >
              <Copy size={15} />
            </button>
          </div>
          <div className="brief-chips">
            {[
              ['name', context.draft.name],
              ['age', context.draft.age],
              ['languageField', context.draft.language],
              ['place', context.draft.place],
            ]
              .filter(([, v]) => v)
              .map(([label, value]) => (
                <span key={label}>
                  <small>{t(label!)}</small>
                  {value}
                </span>
              ))}
          </div>
          <button
            className="brief-expand"
            onClick={() => setShowBrief(!showBrief)}
            aria-expanded={showBrief}
          >
            {t('originalDescription')}
            {showBrief ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showBrief && <p className="brief-description">{context.description}</p>}
        </section>
        <section className={`agent-workbench ${done ? 'agents-finished' : ''}`}>
          <div className="workbench-heading">
            <div>
              <Sparkles size={17} />
              <h2>{t('agentActivity')}</h2>
              <span className="agents-count">4 {t('demoAgents')}</span>
            </div>
            <button onClick={() => setShowActivity(!showActivity)} aria-expanded={showActivity}>
              {t(showActivity ? 'hideActivity' : 'showActivity')}
              {showActivity ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
          </div>
          {showActivity && (
            <div className="workbench-body">
              <div className="agent-roster">
                {AGENT_PHASES.map((phase, i) => {
                  const Icon = icons[i];
                  const state =
                    done || i < progress.phase
                      ? 'complete'
                      : i === progress.phase
                        ? 'working'
                        : 'waiting';
                  return (
                    <div className={`agent-worker ${state}`} key={phase.key}>
                      <span className="worker-icon">
                        <Icon size={20} />
                      </span>
                      <div>
                        <h3>{t(`agent_${phase.key}`)}</h3>
                        <p>{t(`task_${phase.key}`)}</p>
                        <span className="worker-status">
                          {state === 'complete' ? (
                            <Check size={11} />
                          ) : state === 'working' ? (
                            <i className="worker-dot" />
                          ) : (
                            <Clock size={10} />
                          )}{' '}
                          {t(`agentStatus_${state}`)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="agent-feed">
                <div className="agent-feed-title">
                  <span>
                    <i className={done ? '' : 'feed-live-dot'} />
                    {t('sampleActivityFeed')}
                  </span>
                  <time>
                    {Math.min(Math.floor(elapsed / 1000), 12)
                      .toString()
                      .padStart(2, '0')}
                    s
                  </time>
                </div>
                <ol aria-live="polite">
                  {AGENT_PHASES.filter((p) => elapsed >= p.at).map((phase, i) => (
                    <li key={phase.key}>
                      <time>
                        00:
                        {Math.floor(phase.at / 1000)
                          .toString()
                          .padStart(2, '0')}
                      </time>
                      <div>
                        <strong>{t(`agent_${phase.key}`)}</strong>
                        <p>{t(`log_${phase.key}`)}</p>
                      </div>
                      {done || i < progress.phase ? (
                        <Check size={13} />
                      ) : (
                        <LoaderCircle size={13} className="spinner" />
                      )}
                    </li>
                  ))}
                  {done && (
                    <li className="feed-completion">
                      <time>00:12</time>
                      <div>
                        <strong>{t('rankingReady')}</strong>
                        <p>{t('rankingReadyDesc')}</p>
                      </div>
                      <Check size={14} />
                    </li>
                  )}
                </ol>
                {!done && (
                  <div className="agent-feed-caption">
                    <span className="agent-thinking">
                      <i />
                      <i />
                      <i />
                    </span>
                    {t(`active_${AGENT_PHASES[progress.phase].key}`)}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
        <div role="status" className="sr-only">
          {t(done ? 'demoComplete' : 'demoRunning')}
          {done && ` ${revealed} / 3`}
        </div>
        {done ? (
          <section className="agent-results">
            <div className="agent-results-heading">
              <div>
                <p className="eyebrow">{t('sampleResults')}</p>
                <h2>{t('candidatesRanked', { count: 3 })}</h2>
                <p>{t('scoreExplanation')}</p>
              </div>
              <Button variant="outline" onClick={replay}>
                <RotateCcw size={14} />
                {t('replayDemo')}
              </Button>
            </div>
            {matches.slice(0, revealed).map((match, i) => (
              <ResultCard key={match.id} match={match} index={i} />
            ))}
            {revealed < 3 && (
              <div className="next-sample-reveal">
                <LoaderCircle className="spinner" size={16} />
                {t('revealingNext')}
                <button onClick={() => setManualReveal(true)}>{t('showAllNow')}</button>
              </div>
            )}
            <p className="agent-results-disclaimer">
              <ShieldCheck size={17} />
              {t('scoreDisclaimer')}
            </p>
            <div className="agent-bottom-actions">
              {context.caseNo && (
                <ActionLink href={`/case/${encodeURIComponent(context.caseNo)}`} variant="outline">
                  {t('checkCase')}
                  <ArrowUpRight size={15} />
                </ActionLink>
              )}
              {onStartNew ? (
                <Button variant="plain" onClick={onStartNew}>
                  {t('differentSearch')}
                  <ArrowRight size={15} />
                </Button>
              ) : (
                <ActionLink href="/search?new=1" variant="plain">
                  {t('differentSearch')}
                  <ArrowRight size={15} />
                </ActionLink>
              )}
            </div>
          </section>
        ) : (
          <div className="agent-results-waiting">
            <div className="waiting-file">
              <Users size={24} />
              <ScanSearch size={16} />
            </div>
            <div>
              <strong>{t('resultsWillAppear')}</strong>
              <p>{t('resultsWillAppearDesc')}</p>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
