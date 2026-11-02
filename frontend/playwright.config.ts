import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    viewport: { width: 1366, height: 768 },
    video: process.env.RECORD_EVIDENCE === '1' ? 'on' : 'off',
    trace: 'retain-on-failure',
    launchOptions: process.env.CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.CHROMIUM_EXECUTABLE }
      : {},
  },
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: 'NEXT_PUBLIC_DEMO=1 npm run dev -- --port 3000',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
      },
});
