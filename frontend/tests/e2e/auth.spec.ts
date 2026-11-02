import { test, expect, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { artifactPath } from '../../scripts/paths.mjs';
const mobile = () => String(9100000000 + Math.floor(Math.random() * 800000000));
async function language(page: Page) {
  await page.addInitScript(() => localStorage.setItem('khoj-language', 'en'));
}
async function signIn(page: Page, phone: string) {
  await page.getByLabel('Mobile number', { exact: true }).fill(phone);
  await page.getByRole('button', { name: 'Send verification code', exact: true }).click();
  await page.getByRole('button', { name: 'Fill it for me', exact: true }).click();
  await page.getByRole('button', { name: 'Verify & continue', exact: true }).click();
}

test('guest report reaches Save before OTP, then creates a cookie-owned case', async ({
  page,
  context,
  browser,
}) => {
  await language(page);
  await page.goto('/report/missing');
  await expect(page.locator('#answer')).toHaveCount(1);
  await expect(page.getByLabel('Mobile number', { exact: true })).toHaveCount(0);
  await page
    .locator('#answer')
    .fill(
      'My brother Rahul is about 24 years old. He speaks Hindi and has a scar on his left eyebrow. He was last seen at New Delhi station on Friday evening.',
    );
  await page.getByRole('button', { name: 'Organize my description', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A familiar face can help.' })).toBeVisible();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Does this sound right?' })).toBeVisible();
  await expect(page.getByLabel('Mobile number', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Yes, that’s correct', exact: true }).click();
  await expect(page.getByLabel('Mobile number', { exact: true })).toBeVisible();
  const phone = mobile();
  await page.getByLabel('Mobile number', { exact: true }).fill(phone);
  await page.getByRole('button', { name: 'Send verification code', exact: true }).click();
  await expect(page.getByText('Demo mode: OTP is 123456', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Fill it for me', exact: true })).toBeEnabled();
  await mkdir(artifactPath('f2', 'accepted'), { recursive: true });
  await page.screenshot({ path: artifactPath('f2', 'accepted', 'report-save-otp.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const box of await page.locator('.otp-boxes input').all()) {
    const bounds = await box.boundingBox();
    expect(bounds!.width).toBeGreaterThanOrEqual(48);
    expect(bounds!.height).toBeGreaterThanOrEqual(48);
  }
  await page.screenshot({ path: artifactPath('f2', 'accepted', 'report-save-otp-mobile.png') });
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.getByRole('button', { name: 'Fill it for me', exact: true }).click();
  await page.getByRole('button', { name: 'Verify & continue', exact: true }).click();
  await expect(page).toHaveURL(/\/search\?case=KHJ-\d{4}-\d{5,}/);
  const bypass = await context.request.post('/api/demo/reports', {
    data: { sessionId: crypto.randomUUID(), kind: 'missing' },
  });
  expect(bypass.status()).toBe(409);
  const caseNo = new URL(page.url()).searchParams.get('case')!;
  const other = await browser.newContext();
  const otherPhone = mobile();
  await other.request.post('/api/auth/otp/send', { data: { phone: otherPhone } });
  await other.request.post('/api/auth/otp/verify', { data: { phone: otherPhone, code: '123456' } });
  expect((await other.request.get(`/api/case/${caseNo}`)).status()).toBe(404);
  expect((await other.request.get('/api/cases')).status()).toBe(200);
  await other.close();
  const cookies = await context.cookies();
  expect(cookies.find((c) => c.name === 'khoj_session')).toMatchObject({
    httpOnly: true,
    secure: true,
    sameSite: 'Lax',
  });
  expect(await page.evaluate(() => document.cookie)).not.toContain('khoj_session');
  const storage = await page.evaluate(() =>
    JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }),
  );
  expect(storage).not.toContain(phone);
  expect(storage).not.toContain('123456');
  await page.goto('/cases');
  await expect(page.locator('.case-list-card')).toHaveCount(1);
  await page.screenshot({ path: artifactPath('f2', 'accepted', 'my-cases.png') });
  await page.getByLabel(/^Account/).click();
  await page.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page).toHaveURL('/');
  const me = await context.request.get('/api/auth/me');
  expect(me.status()).toBe(401);
});
test('login rejects external next URLs and keeps the account after reload', async ({ page }) => {
  await language(page);
  await page.goto('/login?next=https%3A%2F%2Fattacker.example');
  const phone = mobile();
  await signIn(page, phone);
  await expect(page).toHaveURL('/cases');
  await page.reload();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByLabel(/^Account/)).toBeVisible();
  expect(await page.getByLabel(/^Account/).textContent()).toContain(phone.slice(-2));
});
test('wrong OTP stays editable, then a local redirect succeeds', async ({ page }) => {
  await language(page);
  await page.goto('/login?next=%2Fsearch%3Fnew%3D1');
  await page.getByLabel('Mobile number', { exact: true }).fill(mobile());
  await page.getByRole('button', { name: 'Send verification code', exact: true }).click();
  const digits = page.getByRole('textbox', { name: /Code digit/ });
  for (let i = 0; i < 6; i++) await digits.nth(i).fill('0');
  await page.getByRole('button', { name: 'Verify & continue', exact: true }).click();
  await expect(page.locator('.error-box')).toContainText('That code didn’t match. Try again.');
  await page.getByRole('button', { name: 'Fill it for me', exact: true }).click();
  await page.getByRole('button', { name: 'Verify & continue', exact: true }).click();
  await expect(page).toHaveURL('/search?new=1');
});
test('demo bridge enforces rate limits and role accounts without exposing tokens', async ({
  request,
  page,
}) => {
  const phone = mobile();
  const csrf = await request.post('/api/auth/otp/send', {
    data: { phone },
    headers: { Origin: 'https://attacker.example' },
  });
  expect(csrf.status()).toBe(403);
  for (let i = 0; i < 5; i++)
    expect((await request.post('/api/auth/otp/send', { data: { phone } })).status()).toBe(200);
  const limited = await request.post('/api/auth/otp/send', { data: { phone } });
  expect(limited.status()).toBe(429);
  expect(Number(limited.headers()['retry-after'])).toBeGreaterThan(0);
  await language(page);
  await page.goto('/officer');
  await expect(page.getByText('Not available in demo', { exact: true })).toBeVisible();
  await request.post('/api/auth/otp/send', { data: { phone: '9000000003' } });
  const verify = await request.post('/api/auth/otp/verify', {
    data: { phone: '9000000003', code: '123456' },
  });
  expect(verify.status()).toBe(200);
  const body = await verify.json();
  expect(body.user.role).toBe('officer');
  expect(body).not.toHaveProperty('token');
  expect(body.user).not.toHaveProperty('phone');
});

test('guests can search without an OTP prompt', async ({ page }) => {
  await language(page);
  await page.goto('/search?new=1');
  await page.locator('#search-state').selectOption('DELHI');
  await page.locator('#search-query').fill('A man about 24 years old with a scar on his eyebrow.');
  await page.getByRole('button', { name: 'Search for possible matches', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Your details. A search in motion.' }),
  ).toBeVisible();
  await expect(page.getByLabel('Mobile number', { exact: true })).toHaveCount(0);
});
