// @vitest-environment jsdom
import { useState } from 'react';
import { afterEach, it, expect } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NextIntlClientProvider } from 'next-intl';
import { OtpInputs } from '@/features/auth/OtpInputs';
import en from '@/messages/en.json';
function Harness() {
  const [digits, setDigits] = useState<string[]>(Array(6).fill(''));
  return (
    <NextIntlClientProvider locale="en" messages={en} timeZone="Asia/Kolkata">
      <OtpInputs digits={digits} onChange={setDigits} />
      <output aria-label="Current code">{digits.join('')}</output>
    </NextIntlClientProvider>
  );
}
afterEach(cleanup);
it('advances, supports arrow/backspace editing and keeps all six positions', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const cells = screen.getAllByRole('textbox') as HTMLInputElement[];
  await user.type(cells[0], '12');
  expect(cells[0].value).toBe('1');
  expect(cells[1].value).toBe('2');
  expect(document.activeElement).toBe(cells[2]);
  await user.keyboard('{Backspace}');
  expect(cells[1].value).toBe('');
  expect(document.activeElement).toBe(cells[1]);
  await user.keyboard('{ArrowLeft}');
  expect(document.activeElement).toBe(cells[0]);
});
it('accepts a full pasted code and filters non-digits', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const cells = screen.getAllByRole('textbox') as HTMLInputElement[];
  await user.click(cells[0]);
  await user.paste('12 34-56');
  expect(cells.map((cell) => cell.value).join('')).toBe('123456');
  expect(document.activeElement).toBe(cells[5]);
});
