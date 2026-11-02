import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
const base = process.env.E2E_BASE_URL || 'http://localhost:3001';
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
await context.addCookies([{ name: 'khoj-language', value: 'en', url: base }]);
await context.addInitScript(() => localStorage.setItem('khoj-language', 'en'));
const page = await context.newPage();
const results = [];
async function audit(route, state = 'initial') {
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getComputedTiming().iterations !== Infinity)
        .map((a) => a.finished.catch(() => {})),
    ),
  );
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  results.push({
    route,
    state,
    violations: result.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })),
    })),
  });
}
for (const route of ['/', '/report/missing', '/search', '/login']) {
  await page.goto(base + route);
  await expect(page.locator('h1')).toHaveCount(1);
  await page.locator('h1').waitFor();
  await page.evaluate(() => document.fonts.ready);
  await audit(route);
  if (route === '/report/missing') {
    await page.locator('.record-row').first().scrollIntoViewIfNeeded();
    await audit(route, 'summary');
  }
}
await browser.close();
await mkdir('artifacts/quality', { recursive: true });
await writeFile('artifacts/quality/axe-verified.json', JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
if (results.some((r) => r.violations.length)) process.exitCode = 1;
