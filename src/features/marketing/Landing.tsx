'use client';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import {
  ArrowDown,
  ArrowUpRight,
  Search,
  ShieldCheck,
  Check,
  Plus,
  Minus,
  Heart,
  UserRound,
} from 'lucide-react';
import { useState } from 'react';
import { ActionLink } from '@/components/ui/index';
import { EmergencyStrip } from '@/components/layout/index';
import { HumanArt } from '@/components/illustrations/HumanArt';
const illustrationPeople: Record<string, number> = {
  bird: 0,
  'cat-coffee': 2,
  penguin: 3,
  'girl-jump': 4,
  'bird-with-briefcase': 0,
  'banana-laptop': 3,
  'alligator-on-unicycle': 5,
  croc: 4,
  'duck-on-scooter': 0,
  'crt-monitor': 1,
  'birdy-key': 2,
  'record-card': 1,
  'coffee-time': 5,
};
function Illustration({ name, className = '' }: { name: string; className?: string }) {
  return <HumanArt person={illustrationPeople[name] ?? 0} className={className} />;
}
function Crowd() {
  return <div className="crowd indian-crowd" aria-hidden="true" />;
}
function ExampleReport() {
  const t = useTranslations();
  return (
    <div className="example-report">
      <div className="example-report-head">
        <span>
          <Search size={17} />
          <strong>{t('reportRoom')}</strong>
        </span>
        <span className="demo-chip">{t('example')}</span>
      </div>
      <div className="example-report-body">
        <div className="example-message">
          <div className="avatar avatar-human">
            <UserRound size={20} />
          </div>
          <div>
            <strong>
              {t('family')} <small>9:41</small>
            </strong>
            <p>{t('exampleText')}</p>
          </div>
        </div>
        <div className="example-message">
          <div className="avatar">
            <HumanArt person={5} />
          </div>
          <div>
            <strong>
              {t('assistant')} <span className="tiny-label">KHOJ</span>
            </strong>
            <p>{t('exampleReply')}</p>
          </div>
        </div>
        <div className="example-record">
          <div className="record-heading">
            <span>
              <Check size={17} />
              {t('understood')}
            </span>
            <span className="tiny-label">DEMO</span>
          </div>
          {[
            ['person', 'examplePerson'],
            ['age', 'exampleAge'],
            ['marks', 'exampleMarks'],
            ['place', 'examplePlace'],
          ].map(([label, value]) => (
            <div className="example-field" key={label}>
              <span>{t(label)}</span>
              <strong>{t(value)}</strong>
            </div>
          ))}
          <p className="record-foot">
            <ShieldCheck size={15} />
            {t('reviewNote')}
          </p>
        </div>
      </div>
    </div>
  );
}
export function Landing() {
  const t = useTranslations();
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  return (
    <main id="main">
      <section className="hero">
        <Crowd />
        <div className="hero-card">
          <HumanArt person={0} className="hero-mascot" priority />
          <p className="hero-eyebrow">{t('heroTop')}</p>
          <h1>
            {t('hero1')}
            <br />
            {t('hero2')}
          </h1>
          <p className="hero-description">{t('heroDesc')}</p>
          <div className="hero-buttons">
            <ActionLink href="/report/missing" arrow>
              {t('reportMissing')}
            </ActionLink>
            <ActionLink href="/report/found" variant="outline" arrow>
              {t('reportFound')}
            </ActionLink>
          </div>
          <Link href="/search" className="hero-search">
            <Search size={16} />
            {t('searchDesc')}
            <ArrowUpRight size={15} />
          </Link>
          <p className="hero-footnote">
            {t('freeLine')} <Link href="/case">{t('checkCase')} ↗</Link>
          </p>
        </div>
        <a className="learn-more" href="#meet-khoj">
          {t('learnMore')}
          <ArrowDown size={16} />
        </a>
      </section>
      <EmergencyStrip />
      <div className="landing-content">
        <section id="meet-khoj" className="intro-section section">
          <p className="eyebrow">{t('meet')}</p>
          <h2>
            {t('intro1')} <Illustration name="bird" className="inline-bird" />
            <br />
            {t('intro2')}
            <br />
            <Illustration name="cat-coffee" className="inline-cat" />
            {t('intro3')}
          </h2>
          <p className="intro-description">{t('introDesc')}</p>
          <Illustration name="penguin" className="intro-penguin" />
        </section>
        <section id="how-it-works" className="how-section section">
          <div className="section-copy">
            <p className="eyebrow">{t('howLabel')}</p>
            <h2>
              {t('how1')}
              <br />
              {t('how2')}
            </h2>
            <p>{t('howDesc')}</p>
            <Link href="/report/missing" className="text-link">
              {t('seeHow')}
              <ArrowUpRight size={18} />
            </Link>
            <HumanArt person={1} className="how-fox" />
          </div>
          <ExampleReport />
        </section>
        <section className="together-section section">
          <p className="eyebrow">{t('togetherLabel')}</p>
          <h2>
            {t('together1')}
            <br />
            {t('together2')}
          </h2>
          <div className="together-grid">
            <div className="purpose-card">
              <div className="purpose-card-head">
                <Heart size={19} />
                <strong>{t('tagline')}</strong>
              </div>
              <p>{t('togetherDesc')}</p>
              <div className="purpose-avatars">
                {[0, 1, 2, 3, 5].map((person) => (
                  <HumanArt key={person} person={person} />
                ))}
              </div>
            </div>
            <div className="roles">
              {[
                ['familyRole', 'familyRoleDesc', UserRound],
                ['finderRole', 'finderRoleDesc', Heart],
                ['officerRole', 'officerRoleDesc', ShieldCheck],
              ].map(([title, desc, Icon]) => {
                const I = Icon as typeof Heart;
                return (
                  <div className="role" key={title as string}>
                    <span className="role-icon">
                      <I size={22} />
                    </span>
                    <div>
                      <strong>{t(title as string)}</strong>
                      <p>{t(desc as string)}</p>
                    </div>
                    <Check size={16} />
                  </div>
                );
              })}
            </div>
          </div>
        </section>
        <section className="story-panel">
          <div>
            <span className="eyebrow">{t('tagline')}</span>
            <h2>
              {t('storyTitle')}
              <br />
              {t('storyTitle2')}
            </h2>
            <p>{t('storyDesc')}</p>
            <ActionLink href="/report/missing" arrow>
              {t('getStarted')}
            </ActionLink>
          </div>
          <div className="story-illustration">
            <Illustration name="girl-jump" />
            <span className="story-spark spark-one">✳</span>
            <span className="story-spark spark-two">✧</span>
            <span className="story-spark spark-three">✧</span>
          </div>
        </section>
        <section className="principles-section section">
          <p className="eyebrow">{t('principles')}</p>
          <div className="principles-grid">
            {[
              ['bird-with-briefcase', 'principle1', 'principle1desc'],
              ['banana-laptop', 'principle2', 'principle2desc'],
              ['alligator-on-unicycle', 'principle3', 'principle3desc'],
            ].map(([image, title, desc]) => (
              <article key={title}>
                <Illustration name={image} />
                <h3>{t(title)}</h3>
                <p>{t(desc)}</p>
              </article>
            ))}
          </div>
        </section>
        <section id="why-khoj" className="features-section section">
          <p className="eyebrow">{t('why')}</p>
          <h2>
            {t('why1')}
            <br />
            {t('why2')}
          </h2>
          <div className="feature-grid">
            <article className="feature-card feature-blue feature-tall">
              <div className="croc-stack">
                <HumanArt person={4} className="family-art" />
              </div>
              <div>
                <h3>{t('feature1')}</h3>
                <p>{t('feature1desc')}</p>
                <Link href="/report/found" aria-label={t('reportFound')} className="feature-link">
                  <ArrowUpRight />
                </Link>
              </div>
            </article>
            <article className="feature-card feature-yellow feature-wide">
              <Illustration name="duck-on-scooter" />
              <div>
                <h3>{t('feature2')}</h3>
                <p>{t('feature2desc')}</p>
                <Link href="/report/missing" className="text-link">
                  {t('getStarted')}
                  <ArrowUpRight size={17} />
                </Link>
              </div>
            </article>
            <article className="feature-card feature-pink">
              <Illustration name="crt-monitor" />
              <div>
                <h3>{t('feature3')}</h3>
                <p>{t('feature3desc')}</p>
              </div>
            </article>
            <article className="feature-card feature-peach feature-privacy">
              <Illustration name="birdy-key" />
              <div>
                <h3>{t('feature4')}</h3>
                <p>{t('feature4desc')}</p>
              </div>
            </article>
            <article className="feature-card feature-yellow feature-small">
              <Illustration name="record-card" />
              <div>
                <h3>{t('feature5')}</h3>
                <p>{t('feature5desc')}</p>
              </div>
            </article>
            <article className="feature-card feature-blue feature-small">
              <Illustration name="coffee-time" />
              <div>
                <h3>{t('feature6')}</h3>
                <p>{t('feature6desc')}</p>
              </div>
            </article>
          </div>
        </section>
        <section className="faq-section section">
          <div>
            <p className="eyebrow">{t('questions')}</p>
            <h2>{t('faqTitle')}</h2>
            <Illustration name="cat-coffee" />
          </div>
          <div className="faq-list">
            {[1, 2, 3, 4, 5].map((n) => (
              <div className="faq-item" key={n}>
                <button
                  aria-expanded={openFaq === n}
                  aria-controls={`faq-${n}`}
                  onClick={() => setOpenFaq(openFaq === n ? null : n)}
                >
                  <span className="faq-number">0{n}</span>
                  <span>{t(`faq${n}`)}</span>
                  {openFaq === n ? <Minus size={18} /> : <Plus size={18} />}
                </button>
                <div id={`faq-${n}`} hidden={openFaq !== n}>
                  <p>{t(`faq${n}a`)}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="final-cta">
          <Illustration name="bird" />
          <p className="eyebrow">{t('heroTop')}</p>
          <h2>
            {t('cta')}
            <br />
            {t('cta2')}
          </h2>
          <p>{t('ctaDesc')}</p>
          <div className="hero-buttons">
            <ActionLink href="/report/missing" arrow>
              {t('reportMissing')}
            </ActionLink>
            <ActionLink href="/search" variant="outline">
              {t('searchDesc')}
              <Search size={17} />
            </ActionLink>
          </div>
        </section>
      </div>
    </main>
  );
}
