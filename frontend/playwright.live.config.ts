import { defineConfig } from '@playwright/test';

const apiUrl = process.env.MEMORYHIVE_API_URL ?? 'http://127.0.0.1:8000/api/v1';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/live-workflow.e2e.ts',
  reporter: 'line',
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:3200',
    browserName: 'chromium',
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `VITE_API_URL=${apiUrl} npm run dev -- --host 127.0.0.1 --port 3200`,
    url: 'http://127.0.0.1:3200',
    reuseExistingServer: true,
  },
});
