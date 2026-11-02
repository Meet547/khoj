import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: {
    include: ['tests/**/*.test.{ts,tsx,mjs}'],
    exclude: ['tests/e2e/**'],
    environment: 'node',
    testTimeout: 15000,
    clearMocks: true,
  },
});
