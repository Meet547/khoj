'use client';
import { useEffect, useId, useState } from 'react';
import { useTranslations } from 'next-intl';
import { LoaderCircle, ArrowRight } from 'lucide-react';
import { authApi as api } from '@/lib/api/auth';
import { MOCK, AppError } from '@/lib/api/client';
import { Button, ErrorBox, Modal } from '@/components/ui';
import { useAuth } from './useAuth';
import { OtpInputs } from './OtpInputs';
export function OtpForm({ onVerified }: { onVerified: () => Promise<void> }) {
  const t = useTranslations(),
    { login } = useAuth(),
    id = useId();
  const [phone, setPhone] = useState(''),
    [digits, setDigits] = useState<string[]>(Array(6).fill('')),
    [sent, setSent] = useState(false),
    [timer, setTimer] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [demo, setDemo] = useState(MOCK);
  useEffect(() => {
    if (!timer) return;
    const timeout = setTimeout(() => setTimer((value) => Math.max(0, value - 1)), 1000);
    return () => clearTimeout(timeout);
  }, [timer]);
  function showError(e: unknown) {
    if (e instanceof AppError && e.retryAfter) setTimer(e.retryAfter);
    setError(
      e instanceof AppError && e.code === 'invalid_code'
        ? t('wrongCode')
        : e instanceof Error
          ? e.message
          : t('somethingWrong'),
    );
  }
  async function send() {
    setError('');
    if (!/^[6-9]\d{9}$/.test(phone)) {
      setError(t('invalidPhone'));
      return;
    }
    setBusy(true);
    try {
      const result = await api.sendOtp(phone);
      setDemo(result.demo);
      setSent(true);
      setTimer(30);
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  }
  async function verify() {
    setError('');
    if (digits.some((value) => !value)) {
      setError(t('enterSixDigits'));
      return;
    }
    setBusy(true);
    try {
      await login(phone, digits.join(''));
      setPhone('');
      setDigits(Array(6).fill(''));
      await onVerified();
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="otp-form"
      onSubmit={(e) => {
        e.preventDefault();
        void (sent ? verify() : send());
      }}
    >
      {demo && (
        <div className="demo-auth-chip" role="note">
          {t('demoCode')}
        </div>
      )}
      {!sent ? (
        <>
          <label className="field-label" htmlFor={id + '-phone'}>
            {t('phone')}
          </label>
          <div className="phone-input">
            <span aria-hidden="true">+91</span>
            <input
              id={id + '-phone'}
              className="input"
              type="tel"
              inputMode="numeric"
              autoComplete="tel-national"
              placeholder="98765 43210"
              required
              value={phone.replace(/(\d{5})(?=\d)/, '$1 ')}
              onChange={(e) => {
                setPhone(
                  e.target.value
                    .replace(/\D/g, '')
                    .replace(/^91(?=\d{10}$)/, '')
                    .slice(0, 10),
                );
                setError('');
              }}
              aria-describedby={error ? id + '-error' : undefined}
              disabled={busy}
              maxLength={16}
            />
          </div>
        </>
      ) : (
        <>
          <p className="otp-destination">{t('codeSentMasked', { suffix: phone.slice(-2) })}</p>
          <label className="field-label">{t('code')}</label>
          <OtpInputs
            digits={digits}
            onChange={(value) => {
              setDigits(value);
              setError('');
            }}
            disabled={busy}
            errorId={error ? id + '-error' : undefined}
          />
          {demo && (
            <Button
              type="button"
              variant="outline"
              className="fill-code"
              onClick={() => {
                setDigits('123456'.split(''));
                setError('');
              }}
              disabled={busy}
            >
              {t('fillCode')}
            </Button>
          )}
        </>
      )}
      {error && (
        <div id={id + '-error'}>
          <ErrorBox message={error} />
        </div>
      )}
      <Button
        type="submit"
        disabled={busy || (sent && digits.some((value) => !value))}
        className="w-full mt-5"
      >
        {busy ? <LoaderCircle className="spinner" size={18} /> : <ArrowRight size={17} />}{' '}
        {t(sent ? 'verify' : 'sendCode')}
      </Button>
      {sent && (
        <div className="otp-secondary">
          <button
            type="button"
            className="resend-button"
            disabled={busy || timer > 0}
            onClick={() => void send()}
          >
            {timer ? t('resendIn', { seconds: timer }) : t('resend')}
          </button>
          <button
            type="button"
            className="resend-button"
            disabled={busy}
            onClick={() => {
              setSent(false);
              setDigits(Array(6).fill(''));
              setError('');
            }}
          >
            {t('change')}
          </button>
        </div>
      )}
    </form>
  );
}
export function OtpDialog({
  open,
  onOpenChange,
  onVerified,
  title,
  description,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onVerified: () => Promise<void>;
  title?: string;
  description?: string;
}) {
  const t = useTranslations();
  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title || t('phoneDesc')}
      description={description || t('consent')}
    >
      <OtpForm
        onVerified={async () => {
          await onVerified();
          onOpenChange(false);
        }}
      />
    </Modal>
  );
}
