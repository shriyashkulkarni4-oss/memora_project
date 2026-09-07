#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const { PNG } = require("pngjs");

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const mobileRoot = path.resolve(scriptDir, "..");
const outputDir = path.join(mobileRoot, "store-assets");

const colors = {
  ink: "#18201f",
  muted: "#5d6a66",
  primary: "#0f766e",
  primaryDark: "#173b37",
  primarySoft: "#e2f2ef",
  paper: "#f7f8f6",
  white: "#ffffff",
  gold: "#f4c95d",
};

function htmlDocument(body, width, height) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    * { box-sizing: border-box; }
    html, body { width: ${width}px; height: ${height}px; margin: 0; overflow: hidden; }
    body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: ${colors.ink}; background: ${colors.paper}; }
    svg { display: block; }
  </style>
</head>
<body>${body}</body>
</html>`;
}

function brandGlyph(size = 420) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 512 512" aria-hidden="true">
  <defs>
    <linearGradient id="bookFill" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#dff5f1"/>
    </linearGradient>
  </defs>
  <g fill="none" stroke="rgba(255,255,255,.34)" stroke-width="10">
    <path d="M104 132h304M104 256h304M104 380h304M132 104v304M256 92v328M380 104v304"/>
    <path d="M132 132l248 248M380 132L132 380"/>
  </g>
  <path d="M126 164c0-34 28-62 62-62h196v56H196c-10 0-18 8-18 18v158c0 10 8 18 18 18h188v58H188c-34 0-62-28-62-62V164Z" fill="url(#bookFill)"/>
  <path d="M204 166h180c36 0 66 30 66 66v145c0 19-15 34-34 34H226c-24 0-44-20-44-44V188c0-12 10-22 22-22Z" fill="rgba(23,59,55,.22)"/>
  <path d="M206 192h184c18 0 32 14 32 32v120c0 18-14 32-32 32H206V192Z" fill="#ffffff"/>
  <path d="M232 226h132M232 264h148M232 302h100" stroke="${colors.primary}" stroke-width="18" stroke-linecap="round"/>
  <path d="M380 192v86l-32-20-32 20v-86h64Z" fill="${colors.gold}"/>
</svg>`;
}

function iconMarkup() {
  return `<main style="position:relative;width:1024px;height:1024px;background:linear-gradient(145deg,#173b37 0%,#0f766e 58%,#145b50 100%);">
  <div style="position:absolute;inset:74px;border-radius:216px;background:linear-gradient(160deg,rgba(255,255,255,.18),rgba(255,255,255,.05));box-shadow:inset 0 0 0 2px rgba(255,255,255,.18);"></div>
  <div style="position:absolute;inset:132px;border-radius:176px;background:rgba(255,255,255,.09);box-shadow:0 44px 120px rgba(0,0,0,.24);"></div>
  <div style="position:absolute;left:252px;top:252px;width:520px;height:520px;border-radius:132px;background:${colors.white};display:flex;align-items:center;justify-content:center;box-shadow:0 42px 90px rgba(0,0,0,.28);">
    <div style="width:424px;height:424px;border-radius:108px;background:${colors.primary};display:flex;align-items:center;justify-content:center;overflow:hidden;">
      ${brandGlyph(360)}
    </div>
  </div>
</main>`;
}

function featureGraphicMarkup() {
  return `<main style="position:relative;width:1024px;height:500px;background:linear-gradient(135deg,#f7f8f6 0%,#e2f2ef 46%,#f4c95d 140%);overflow:hidden;">
  <div style="position:absolute;left:42px;top:48px;width:164px;height:164px;border-radius:36px;background:${colors.primary};display:flex;align-items:center;justify-content:center;box-shadow:0 18px 38px rgba(15,118,110,.24);">${brandGlyph(128)}</div>
  <section style="position:absolute;left:64px;top:236px;width:380px;">
    <p style="margin:0 0 8px;color:${colors.primary};font-size:18px;font-weight:800;letter-spacing:0;text-transform:uppercase;">Memoryhive</p>
    <h1 style="margin:0;color:${colors.ink};font-size:54px;line-height:1.02;font-weight:820;letter-spacing:0;">Capture. Tag. Find.</h1>
    <p style="margin:18px 0 0;color:${colors.muted};font-size:21px;line-height:1.35;font-weight:550;">An offline-first library for links, screenshots, and notes.</p>
  </section>
  <section style="position:absolute;right:58px;top:58px;width:462px;height:384px;border-radius:30px;background:${colors.white};box-shadow:0 32px 80px rgba(24,32,31,.14);padding:28px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:22px;">
      <strong style="font-size:23px;">Library</strong>
      <span style="padding:8px 12px;border-radius:999px;background:${colors.primarySoft};color:${colors.primary};font-size:15px;font-weight:800;">248 saved</span>
    </div>
    <div style="height:48px;border:2px solid #dfe5e2;border-radius:16px;display:flex;align-items:center;padding:0 16px;color:${colors.muted};font-size:17px;margin-bottom:18px;">Search notes, links, screenshots</div>
    ${["Design research", "Receipt OCR", "Travel plan"].map((title, index) => `
      <article style="display:grid;grid-template-columns:54px 1fr;gap:14px;align-items:center;height:72px;border-top:${index === 0 ? "0" : "1px"} solid #e6ece9;">
        <div style="width:54px;height:54px;border-radius:16px;background:${index === 1 ? colors.gold : colors.primarySoft};display:flex;align-items:center;justify-content:center;color:${index === 1 ? colors.ink : colors.primary};font-size:24px;font-weight:900;">${index === 1 ? "T" : "#"}</div>
        <div>
          <strong style="display:block;font-size:18px;margin-bottom:7px;">${title}</strong>
          <span style="display:inline-block;padding:5px 9px;border-radius:999px;background:#f1f5f3;color:${colors.muted};font-size:13px;font-weight:750;">${index === 0 ? "favorite" : index === 1 ? "screenshot" : "tagged"}</span>
        </div>
      </article>`).join("")}
  </section>
</main>`;
}

async function renderPng(browser, width, height, body, outputPath) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(htmlDocument(body, width, height), { waitUntil: "load" });
  const screenshot = await page.screenshot({ type: "png", omitBackground: false });
  await page.close();

  // Store assets should be opaque RGB PNGs, so remove the screenshot alpha channel.
  const png = PNG.sync.read(screenshot);
  fs.writeFileSync(outputPath, PNG.sync.write(png, { colorType: 2, inputColorType: 6 }));
}

async function main() {
  fs.mkdirSync(path.join(outputDir, "screenshots"), { recursive: true });
  const browser = await chromium.launch();
  try {
    await renderPng(browser, 1024, 1024, iconMarkup(), path.join(outputDir, "icon-1024.png"));
    await renderPng(browser, 1024, 500, featureGraphicMarkup(), path.join(outputDir, "feature-graphic.png"));
  } finally {
    await browser.close();
  }

  const manifest = {
    generator: "cml-memoryhive-mobile/scripts/generate-store-assets.mjs",
    assets: [
      {
        path: "cml-memoryhive-mobile/store-assets/icon-1024.png",
        dimensions: "1024x1024",
        purpose: "Store icon source",
        alt_text: "Memoryhive app icon with a teal personal-library mark.",
      },
      {
        path: "cml-memoryhive-mobile/store-assets/feature-graphic.png",
        dimensions: "1024x500",
        purpose: "Google Play feature graphic",
        alt_text: "Memoryhive branded graphic showing a searchable library for links, screenshots, and notes.",
      },
    ],
  };
  fs.writeFileSync(
    path.join(outputDir, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );

  console.log("Generated cml-memoryhive-mobile/store-assets/icon-1024.png");
  console.log("Generated cml-memoryhive-mobile/store-assets/feature-graphic.png");
  console.log("Generated cml-memoryhive-mobile/store-assets/manifest.json");
}

await main();
