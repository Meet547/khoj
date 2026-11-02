'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Globe, Mic, Keyboard, ArrowUpRight, Menu, X, Phone } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useApp } from '@/components/providers';
import { Modal, ActionLink } from '@/components/ui/index';
import { AccountMenu } from '@/features/auth/AccountMenu';
import { locales, isTranslated } from '@/lib/i18n/config';
export const DEMO = process.env.NEXT_PUBLIC_DEMO === '1';
export function Logo() {
  return (
    <Link href="/" aria-label="KHOJ home" className="logo">
      <span className="logo-wordmark">khoj</span>
    </Link>
  );
}
export function Header() {
  const t = useTranslations();
  const path = usePathname();
  const { lang, setLang, mode, setMode, languageChosen, preferencesReady } = useApp();
  const [languageOpen, setLanguageOpen] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [dockHidden, setDockHidden] = useState(false);
  const landing = path === '/';
  const task = /^\/(report|search|case|cases|login|officer)(\/|$)/.test(path);
  useEffect(() => {
    if (preferencesReady && !languageChosen) setLanguageOpen(true);
  }, [preferencesReady, languageChosen]);
  useEffect(() => {
    const viewport = document.querySelector<HTMLElement>('.page-scroll');
    const position = () =>
      window.matchMedia('(max-width: 1023px)').matches ? viewport?.scrollTop || 0 : window.scrollY;
    let previous = position();
    const scroll = () => {
      const current = position();
      if (Math.abs(current - previous) < 8) return;
      if (!document.activeElement?.closest('.floating-controls'))
        setDockHidden(current > previous && current > 60);
      previous = current;
    };
    const keyboard = () =>
      setDockHidden(
        Boolean(window.visualViewport && window.visualViewport.height < window.innerHeight * 0.72),
      );
    window.addEventListener('scroll', scroll, { passive: true });
    viewport?.addEventListener('scroll', scroll, { passive: true });
    window.visualViewport?.addEventListener('resize', keyboard);
    return () => {
      window.removeEventListener('scroll', scroll);
      viewport?.removeEventListener('scroll', scroll);
      window.visualViewport?.removeEventListener('resize', keyboard);
    };
  }, []);
  useEffect(() => {
    document.querySelector('.page-scroll')?.scrollTo({ top: 0, behavior: 'instant' });
  }, [path]);
  const controls = (
    <>
      <div className="dock-mode" role="group" aria-label={t('inputMode')}>
        <button
          type="button"
          className={mode === 'text' ? 'is-active' : ''}
          aria-pressed={mode === 'text'}
          onClick={() => setMode('text')}
        >
          <Keyboard size={18} />
          <span>{t('text')}</span>
        </button>
        <button
          type="button"
          className={mode === 'voice' ? 'is-active' : ''}
          aria-pressed={mode === 'voice'}
          onClick={() => setMode('voice')}
        >
          <Mic size={18} />
          <span>{t('voice')}</span>
        </button>
      </div>
      <span className="dock-divider" aria-hidden="true" />
      <button
        type="button"
        className="dock-language"
        onClick={() => setLanguageOpen(true)}
        aria-label={`${t('chooseLanguage')}: ${locales.find(({ code }) => code === lang)?.label}`}
      >
        <Globe size={17} />
        <span>{locales.find(({ code }) => code === lang)?.label}</span>
      </button>
    </>
  );
  return (
    <>
      <a className="skip-link" href="#main">
        {t('skipContent')}
      </a>
      <header className={landing ? 'site-header landing-header' : 'site-header app-header'}>
        <nav
          className={`nav-pill ${task ? 'workflow-nav' : 'marketing-nav'}`}
          aria-label="Main navigation"
        >
          <Logo />
          {task ? (
            <div className="workflow-links">
              <Link href="/">{t('exit')}</Link>
              <Link href="/help">{t('navHelp')}</Link>
            </div>
          ) : (
            <div className="desktop-nav">
              <Link href="/#how-it-works">{t('navHow')}</Link>
              <Link href="/search">{t('navSearch')}</Link>
              <Link href="/#why-khoj">{t('navAbout')}</Link>
              <Link href="/help">{t('navHelp')}</Link>
            </div>
          )}
          <div className="header-controls" role="toolbar" aria-label={t('accessibilityControls')}>
            {controls}
          </div>
          <div className="nav-actions">
            <AccountMenu />
            <button
              type="button"
              className="icon-button header-language-mobile"
              aria-label={t('chooseLanguage')}
              onClick={() => setLanguageOpen(true)}
            >
              <Globe size={18} />
            </button>
            {!task && (
              <>
                <Link className="nav-cta" href="/report/missing">
                  {t('getStarted')}
                  <ArrowUpRight size={16} />
                </Link>
                <button
                  type="button"
                  className="icon-button mobile-menu"
                  aria-label={mobile ? t('close') : t('menu')}
                  aria-expanded={mobile}
                  onClick={() => setMobile(!mobile)}
                >
                  {mobile ? <X /> : <Menu />}
                </button>
              </>
            )}
          </div>
          {mobile && !task && (
            <div className="mobile-links">
              {[
                ['/#how-it-works', 'navHow'],
                ['/search', 'navSearch'],
                ['/#why-khoj', 'navAbout'],
                ['/help', 'navHelp'],
              ].map(([href, key]) => (
                <Link href={href} key={key} onClick={() => setMobile(false)}>
                  {t(key)}
                </Link>
              ))}
            </div>
          )}
        </nav>
      </header>
      <div
        className="floating-controls"
        data-hidden={dockHidden || languageOpen}
        inert={dockHidden || languageOpen}
        role="toolbar"
        aria-label={t('accessibilityControls')}
      >
        {controls}
      </div>
      <Modal
        open={languageOpen}
        onOpenChange={(open) => {
          if (!open && !languageChosen) setLang(lang);
          setLanguageOpen(open);
        }}
        title={t('chooseLanguage')}
        description={t('languageIntro')}
      >
        <div className="language-grid">
          {locales.map(({ code, label }) => (
            <button
              type="button"
              lang={code}
              key={code}
              className={lang === code ? 'selected' : ''}
              onClick={() => {
                setLang(code);
                setLanguageOpen(false);
              }}
            >
              {label}
              <small>{lang === code ? '✓' : !isTranslated(code) ? t('comingSoon') : ''}</small>
            </button>
          ))}
        </div>
      </Modal>
    </>
  );
}
export function EmergencyStrip() {
  const t = useTranslations();
  const { lang } = useApp();
  return (
    <div className="emergency-strip">
      <span>
        <Phone size={12} />
        {t('emergency')}: <a href="tel:112">112</a>
      </span>
      <span className="strip-dot">·</span>
      <span>
        {t('child')}: <a href="tel:1098">1098</a>
      </span>
      {DEMO && <span className="strip-demo-notice">{t('demoLocal')}</span>}
      {!isTranslated(lang) && <span className="strip-demo-notice">{t('placeholderLocale')}</span>}
    </div>
  );
}
export function Footer() {
  const t = useTranslations();
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-top">
          <p className="footer-motto">
            {t('footerLine1')}
            <br />
            {t('footerLine2')}
          </p>
          <div className="footer-links">
            <div>
              <span>{t('explore')}</span>
              <Link href="/report/missing">{t('reportMissing')}</Link>
              <Link href="/report/found">{t('reportFound')}</Link>
              <Link href="/search">{t('searchDesc')}</Link>
              <Link href="/#how-it-works">{t('how')}</Link>
            </div>
            <div>
              <span>{t('support')}</span>
              <Link href="/help">{t('navHelp')}</Link>
              <Link href="/help#privacy">{t('privacy')}</Link>
              <Link href="/case">{t('checkCase')}</Link>
            </div>
            <div>
              <span>{t('begin')}</span>
              <ActionLink href="/report/missing" variant="outline">
                {t('getStarted')}
                <ArrowUpRight size={16} />
              </ActionLink>
              <a href="tel:112">{t('emergency')}: 112</a>
            </div>
          </div>
        </div>
        <Link href="/" className="footer-wordmark" aria-label="KHOJ home">
          khoj<span className="wordmark-dot">.</span>
        </Link>
        <div className="footer-bottom">
          <span>{t('copyright')}</span>
          <span>{t('footerNote')}</span>
          <span>{t('footerSafety')}</span>
          <p className="independent-note">{t('independent')}</p>
        </div>
      </div>
    </footer>
  );
}
export function PageTop({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="page-top">
      <Link className="back-link" href="/">
        ← {useTranslations()('home')}
      </Link>
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {description && <p className="page-description">{description}</p>}
    </div>
  );
}
export function SafetyBanner() {
  const t = useTranslations();
  return (
    <aside className="safety-banner">
      <Phone size={22} />
      <div>
        <p>{t('safety')}</p>
        <div>
          <a href="tel:112">{t('callEmergency')} ↗</a>
          <a href="tel:1098">{t('callChild')} ↗</a>
        </div>
      </div>
    </aside>
  );
}
