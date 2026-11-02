import { test, expect } from '@playwright/test';
async function english(page: import('@playwright/test').Page) {
  await page.addInitScript(() => localStorage.setItem('khoj-language', 'en'));
}
test('first visit offers ten native-script languages and remembers the choice', async ({
  page,
}) => {
  await page.goto('/');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  for (const label of [
    'हिन्दी',
    'मराठी',
    'বাংলা',
    'தமிழ்',
    'ਪੰਜਾਬੀ',
    'ગુજરાતી',
    'ಕನ್ನಡ',
    'മലയാളം',
    'తెలుగు',
    'English',
  ])
    await expect(dialog.getByRole('button', { name: label, exact: false })).toBeEnabled();
  await dialog.getByRole('button', { name: 'हिन्दी', exact: false }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'hi');
  await page.reload();
  await expect(dialog).not.toBeVisible();
  expect(
    (await page.context().cookies()).some((c) => c.name === 'khoj-language' && c.value === 'hi'),
  ).toBe(true);
});
for (const viewport of [
  { width: 1366, height: 768 },
  { width: 390, height: 844 },
  { width: 360, height: 800 },
]) {
  test(`layout and intake remain usable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await english(page);
    for (const path of ['/', '/report/missing', '/search']) {
      await page.goto(path);
      await expect(page.locator('h1')).toHaveCount(1);
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
        .toBe(true);
      const dock = page.locator('.floating-controls');
      if (viewport.width >= 1024) await expect(dock).not.toBeVisible();
      else await expect(dock).toBeVisible();
      if (path === '/report/missing') {
        await expect(
          page.locator('header').getByRole('link', { name: 'How it works', exact: true }),
        ).not.toBeVisible();
        await expect(page.locator('#answer')).toBeVisible();
        const answer = await page.locator('#answer').boundingBox();
        expect(answer!.y).toBeLessThan(viewport.height);
        if (viewport.width >= 1024) {
          const action = await page.locator('button[type=submit]').boundingBox();
          expect(action!.y + action!.height).toBeLessThan(viewport.height);
        }
        await page.getByRole('button', { name: 'Speak instead', exact: true }).click();
        await expect(page.locator('#live-transcript')).toBeVisible();
      }
    }
  });
}
test('mobile dock hides on downward scroll and returns on upward scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await english(page);
  await page.goto('/');
  await expect(page.locator('.floating-controls')).toBeVisible();
  await page.evaluate(() => document.querySelector('.page-scroll')?.scrollTo(0, 600));
  await expect(page.locator('.floating-controls')).toHaveAttribute('data-hidden', 'true');
  await page.evaluate(() => document.querySelector('.page-scroll')?.scrollTo(0, 200));
  await expect(page.locator('.floating-controls')).toHaveAttribute('data-hidden', 'false');
});
