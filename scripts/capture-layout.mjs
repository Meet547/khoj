import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
const directory = process.env.SCREENSHOT_DIR || 'artifacts/f0/accepted';
await mkdir(directory, { recursive: true });
const browser = await chromium.launch();
const checks = [];
for (const lang of ['en', 'hi', 'ta'])
  for (const [width, height] of [
    [1366, 768],
    [390, 844],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: 'reduce',
    });
    await context.addCookies([{ name: 'khoj-language', value: lang, url: base }]);
    await context.addInitScript((value) => localStorage.setItem('khoj-language', value), lang);
    const page = await context.newPage();
    for (const route of lang === 'ta' ? ['/'] : ['/', '/report/missing', '/search']) {
      await page.goto(base + route);
      await expect(page.locator('h1')).toHaveCount(1);
      await page.locator('h1').waitFor();
      if (route === '/report/missing') await page.locator('#answer').waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(200);
      const name =
        (route === '/' ? 'home' : route.slice(1).replaceAll('/', '-')) + `-${lang}-${width}`;
      const result = await page.evaluate(() => {
        const dock = document.querySelector('.floating-controls');
        const scroll = document.querySelector('.page-scroll');
        const d = dock.getBoundingClientRect();
        const s = scroll.getBoundingClientRect();
        const action = document
          .querySelector('.report-main button[type=submit]')
          ?.getBoundingClientRect();
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          dockVisible: getComputedStyle(dock).display !== 'none',
          reserved: innerWidth >= 1024 || s.bottom <= d.top,
          actionBottom: action?.bottom,
        };
      });
      if (
        result.overflow ||
        !result.reserved ||
        (width >= 1024 && result.dockVisible) ||
        (width >= 1024 && result.actionBottom > height)
      )
        throw new Error(name + ' layout failed: ' + JSON.stringify(result));
      await page.screenshot({ path: `${directory}/${name}.png` });
      checks.push({ name, ...result });
    }
    await context.close();
  }
await browser.close();
await writeFile(`${directory}/checks.json`, JSON.stringify(checks, null, 2));
console.log(`${checks.length} screenshots and geometry checks passed.`);
