'use client';
import { useRef } from 'react';
import { useTranslations } from 'next-intl';
export function OtpInputs({
  digits,
  onChange,
  disabled = false,
  errorId,
}: {
  digits: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  errorId?: string;
}) {
  const t = useTranslations(),
    refs = useRef<Array<HTMLInputElement | null>>([]);
  function distribute(text: string, index: number) {
    const numbers = text.replace(/\D/g, '').slice(0, 6);
    if (!numbers) return;
    const start = numbers.length === 6 ? 0 : index;
    const next = [...digits];
    for (let i = 0; i < numbers.length && start + i < 6; i++) next[start + i] = numbers[i];
    onChange(next);
    refs.current[Math.min(5, start + numbers.length)]?.focus();
  }
  return (
    <div className="otp-boxes" role="group" aria-label={t('code')}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => {
            refs.current[index] = node;
          }}
          value={digit}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={6}
          autoFocus={index === 0}
          disabled={disabled}
          aria-label={t('codeDigit', { index: index + 1, total: 6 })}
          aria-describedby={errorId}
          onFocus={(e) => e.currentTarget.select()}
          onChange={(e) => {
            if (e.target.value) distribute(e.target.value, index);
            else {
              const next = [...digits];
              next[index] = '';
              onChange(next);
            }
          }}
          onPaste={(e) => {
            e.preventDefault();
            distribute(e.clipboardData.getData('text'), index);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Backspace') {
              e.preventDefault();
              const next = [...digits];
              if (next[index]) next[index] = '';
              else if (index > 0) {
                next[index - 1] = '';
                refs.current[index - 1]?.focus();
              }
              onChange(next);
            } else if (e.key === 'ArrowLeft' && index > 0) {
              e.preventDefault();
              refs.current[index - 1]?.focus();
            } else if (e.key === 'ArrowRight' && index < 5) {
              e.preventDefault();
              refs.current[index + 1]?.focus();
            }
          }}
        />
      ))}
    </div>
  );
}
