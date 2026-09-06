#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const mobileRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(mobileRoot, "..");
const screenshotsDir = path.join(mobileRoot, "store-assets", "screenshots");

const apiUrl =
  process.env.MEMORYHIVE_API_URL ||
  process.env.EXPO_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api/v1";
const baseUrl = process.env.MOBILE_STORE_BASE_URL || "http://127.0.0.1:8083";
const demoEmail = process.env.MOBILE_STORE_DEMO_EMAIL || "engineer@demo.memoryhive.app";
const demoPassword = process.env.MOBILE_STORE_DEMO_PASSWORD || "MemoryhiveDemo123!";

function apiOrigin() {
  const url = new URL(apiUrl);
  return `${url.protocol}//${url.host}`;
}

async function waitForUrl(url, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Keep polling until the caller's timeout. Startup races are expected here.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function demoLogin() {
  try {
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: demoEmail, password: demoPassword }),
    });
    return response.ok ? await response.json() : undefined;
  } catch {
    return undefined;
  }
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd || repoRoot,
      env: { ...process.env, ...options.env },
      stdio: options.stdio || "inherit",
    });
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} exited with ${code}`));
    });
    child.on("error", reject);
  });
}

async function ensureDemoData() {
  console.log("Refreshing engineer demo data.");
  await run("python3", ["seed_data.py", "--base-url", apiOrigin(), "--persona", "engineer"]);
  const seededTokens = await demoLogin();
  if (!seededTokens) {
    throw new Error(`Could not log in as ${demoEmail} after refreshing demo data.`);
  }
  return seededTokens;
}

async function isServing(url) {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch {
    return false;
  }
}

async function startExpoIfNeeded() {
  if (await isServing(baseUrl)) return undefined;
  const port = new URL(baseUrl).port || "8083";
  const child = spawn("npx", ["expo", "start", "--web", "--port", port], {
    cwd: mobileRoot,
    env: {
      ...process.env,
      BROWSER: "none",
      CI: "1",
      EXPO_PUBLIC_API_URL: apiUrl,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.stdout.on("data", (chunk) => process.stdout.write(chunk));
  child.stderr.on("data", (chunk) => process.stderr.write(chunk));
  await waitForUrl(baseUrl, 120_000);
  return child;
}

async function authedPage(browser, tokens, profile) {
  const context = await browser.newContext({
    deviceScaleFactor: profile.deviceScaleFactor,
    hasTouch: true,
    isMobile: profile.isMobile,
    viewport: profile.viewport,
  });
  await context.addInitScript((session) => {
    window.localStorage.setItem("memoryhive.access-token", session.access_token);
    window.localStorage.setItem("memoryhive.refresh-token", session.refresh_token);
  }, tokens);
  return { context, page: await context.newPage() };
}

async function waitForBodyText(page, label, predicate, timeout = 20_000) {
  const startedAt = Date.now();
  let lastText = "";
  while (Date.now() - startedAt < timeout) {
    await dismissDevOverlay(page);
    try {
      lastText = await page.locator("body").innerText({ timeout: 2_000 });
      if (predicate(lastText)) return;
    } catch {
      // Expo web can recreate the root while Metro recovers. Retry until timeout.
    }
    await page.waitForTimeout(1_000);
  }
  throw new Error(
    `Timed out waiting for ${label}. Last body text: ${lastText.slice(0, 400)}`,
  );
}

async function waitForVisibleText(page, text, timeout = 20_000) {
  await waitForBodyText(page, `"${text}"`, (bodyText) => bodyText.includes(text), timeout);
}

async function waitForSavedItems(page) {
  await waitForBodyText(
    page,
    "a non-empty saved item count",
    (bodyText) =>
      Array.from(bodyText.matchAll(/\b(\d+)\s+saved items\b/gi)).some(
        (match) => Number(match[1]) > 0,
      ),
    60_000,
  );
}

async function dismissDevOverlay(page) {
  await page.evaluate(() => {
    document.getElementById("error-overlay")?.remove();
  }).catch(() => undefined);
}

async function capture(page, name) {
  await dismissDevOverlay(page);
  await page.screenshot({ path: path.join(screenshotsDir, name), fullPage: false });
  console.log(`Captured mobile/store-assets/screenshots/${name}`);
}

async function main() {
  fs.mkdirSync(screenshotsDir, { recursive: true });
  const tokens = await ensureDemoData();
  const expo = await startExpoIfNeeded();
  const browser = await chromium.launch();
  const screenshots = [
    {
      name: "iphone-01-library.png",
      platform: "ios",
      form_factor: "iphone",
      dimensions: "1290x2796",
      route: "/home",
      screen: "Library",
      alt_text: "Memoryhive iPhone library showing saved items, favorite counts, tags, and link cards.",
    },
    {
      name: "android-phone-02-search.png",
      platform: "android",
      form_factor: "phone",
      dimensions: "1080x1920",
      route: "/search",
      screen: "Search",
      alt_text: "Memoryhive Android phone search results for FastAPI with saved filters and tags.",
    },
    {
      name: "ipad-03-library.png",
      platform: "ios",
      form_factor: "ipad",
      dimensions: "2048x2732",
      route: "/home",
      screen: "Library",
      alt_text: "Memoryhive iPad library with synced seeded content and reusable tag filters.",
    },
    {
      name: "android-tablet-04-organize.png",
      platform: "android",
      form_factor: "tablet",
      dimensions: "1600x2560",
      route: "/organize",
      screen: "Organize",
      alt_text: "Memoryhive Android tablet organize view showing item counts, types, categories, and tags.",
    },
  ];
  try {
    const profiles = {
      iphone: {
        viewport: { width: 430, height: 932 },
        deviceScaleFactor: 3,
        isMobile: true,
      },
      androidPhone: {
        viewport: { width: 360, height: 640 },
        deviceScaleFactor: 3,
        isMobile: true,
      },
      ipad: {
        viewport: { width: 1024, height: 1366 },
        deviceScaleFactor: 2,
        isMobile: true,
      },
      androidTablet: {
        viewport: { width: 800, height: 1280 },
        deviceScaleFactor: 2,
        isMobile: true,
      },
    };

    const iphone = await authedPage(browser, tokens, profiles.iphone);
    await iphone.page.goto(`${baseUrl}/home`);
    await waitForSavedItems(iphone.page);
    await capture(iphone.page, screenshots[0].name);
    await iphone.context.close();

    const androidPhone = await authedPage(browser, tokens, profiles.androidPhone);
    await androidPhone.page.goto(`${baseUrl}/search`);
    await androidPhone.page.getByLabel("Search saved items").fill("FastAPI");
    await waitForVisibleText(androidPhone.page, "FastAPI async documentation");
    await capture(androidPhone.page, screenshots[1].name);
    await androidPhone.context.close();

    const ipad = await authedPage(browser, tokens, profiles.ipad);
    await ipad.page.goto(`${baseUrl}/home`);
    await waitForSavedItems(ipad.page);
    await capture(ipad.page, screenshots[2].name);
    await ipad.context.close();

    const androidTablet = await authedPage(browser, tokens, profiles.androidTablet);
    await androidTablet.page.goto(`${baseUrl}/organize`);
    await waitForVisibleText(androidTablet.page, "LIBRARY STRUCTURE");
    await waitForVisibleText(androidTablet.page, "#backend", 30_000);
    await capture(androidTablet.page, screenshots[3].name);
    await androidTablet.context.close();

    const manifestPath = path.join(screenshotsDir, "manifest.json");
    fs.writeFileSync(
      manifestPath,
      `${JSON.stringify({
        source: "Expo web preview backed by seeded engineer demo data",
        api_url: apiUrl,
        app_url: baseUrl,
        assets: screenshots,
      }, null, 2)}\n`,
    );
  } finally {
    await browser.close();
    if (expo) expo.kill("SIGTERM");
  }
}

await main();
