import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  reporter: "line",
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:8083",
    browserName: "chromium",
    channel: "chrome",
    viewport: { width: 390, height: 844 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npx expo start --web --port 8083",
    url: "http://127.0.0.1:8083",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
