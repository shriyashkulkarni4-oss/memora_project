#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  assertNoNativeEnvFileFlag,
  loadStoreEnvFile,
  parseStoreScriptArgs,
} from "./store-env.mjs";
import { generatedOutputMismatches } from "./generated-output.mjs";
import { resolveStoreReleaseConfig } from "./store-release-config.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const mobileRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(mobileRoot, "..");
const outputJsonPath = path.join(mobileRoot, "store-assets", "submission-packet.json");
const outputMarkdownPath = path.join(repoRoot, "docs", "Goal-2", "MOBILE_STORE_SUBMISSION_PACKET.md");
let releaseEnvFile;
let checkOnly = false;
try {
  assertNoNativeEnvFileFlag(process.execArgv);
  const cliOptions = parseStoreScriptArgs(process.argv.slice(2));
  const unknownOptions = cliOptions.remainingArgs.filter((arg) => arg !== "--check");
  if (unknownOptions.length) {
    throw new Error(`Unknown option: ${unknownOptions[0]}`);
  }
  checkOnly = cliOptions.remainingArgs.includes("--check");
  releaseEnvFile = loadStoreEnvFile(cliOptions.envFilePath, { repoRoot });
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

function repoPath(relativePath) {
  return path.join(repoRoot, relativePath);
}

function readTextIfExists(relativePath) {
  const fullPath = repoPath(relativePath);
  if (!fs.existsSync(fullPath)) return "";
  return fs.readFileSync(fullPath, "utf8");
}

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(repoPath(relativePath), "utf8"));
}

function envValue(relativePath, name) {
  const match = readTextIfExists(relativePath).match(new RegExp(`^${name}=(.*)$`, "m"));
  const value = match?.[1]?.trim();
  return value || undefined;
}

function requireManifestAsset(manifest, predicate, label) {
  const asset = manifest.assets?.find(predicate);
  if (!asset) throw new Error(`Missing ${label}; regenerate store assets first.`);
  return asset;
}

function markdownList(items) {
  return items.map((item) => `- ${item}`).join("\n");
}

const appConfig = readJson("cml-memoryhive-mobile/app.json").expo;
const assetManifest = readJson("cml-memoryhive-mobile/store-assets/manifest.json");
const screenshotManifest = readJson("cml-memoryhive-mobile/store-assets/screenshots/manifest.json");
const releaseConfig = resolveStoreReleaseConfig({
  readTemplateValue: envValue,
  envFile: releaseEnvFile,
});

const icon = requireManifestAsset(
  assetManifest,
  (asset) => asset.path?.endsWith("icon-1024.png"),
  "store icon metadata",
);
const featureGraphic = requireManifestAsset(
  assetManifest,
  (asset) => asset.path?.endsWith("feature-graphic.png"),
  "Google Play feature graphic metadata",
);
const screenshots = [
  "iphone-01-library.png",
  "android-phone-02-search.png",
  "ipad-03-library.png",
  "android-tablet-04-organize.png",
].map((name) =>
  requireManifestAsset(
    screenshotManifest,
    (asset) => asset.name === name,
    `${name} screenshot metadata`,
  ),
);

const copy = {
  app_store_subtitle: "Capture. Tag. Find.",
  google_play_short_description: "Capture links, screenshots, and notes into a searchable offline-first library.",
  promotional_text: "Save what matters, organize it with tags, and find it again across web and mobile.",
  full_description:
    "Memoryhive is a personal capture and recall app for links, screenshots, and text notes. Save items from your device, add tags and notes, search locally while offline, and sync when you reconnect.",
  features: [
    "Capture links, screenshots, and text notes.",
    "Search by query, item type, status, and tag.",
    "Edit titles, notes, and tags after capture.",
    "Favorite, archive, restore, and delete items with confirmation.",
    "Keep a local offline library and sync changes later.",
    "Export account data and delete your account from Settings.",
  ],
  keywords: "memory, capture, bookmarks, notes, screenshots, knowledge, offline, search, tags, productivity",
};

const privacyDraft = {
  apple_data_types: [
    "Contact Info: email address and optional name.",
    "User Content: photos/screenshots, text notes, links, tags, categories, and generated summaries.",
    "Identifiers: internal user ID.",
    "Usage Data or Diagnostics: only if production logs are treated as product interaction or crash/error diagnostics.",
  ],
  google_data_categories: [
    "Personal info: email address and name.",
    "Photos and videos or files and docs: user-selected screenshots/images.",
    "App activity: app interactions and in-app search/capture activity if retained in logs.",
    "App info and performance or diagnostics: crash/error logs if enabled in production.",
  ],
  tracking: "No, unless a future analytics, ads, or cross-app tracking SDK is added.",
  security:
    "Data is encrypted in transit when production uses HTTPS. Account deletion removes server-owned user data and uploaded assets through the backend lifecycle.",
  external_ai_processing: releaseConfig.privacyDisclosures.external_ai_processing,
  production_telemetry: releaseConfig.privacyDisclosures.production_telemetry,
};

const productionUrls = releaseConfig.urls;
const productionContacts = releaseConfig.contacts;
const storeReviewAccountEmail = releaseConfig.reviewAccountEmail;

const releaseBlockers = [
  "Run EAS init and commit the generated extra.eas.projectId.",
  "Configure public HTTPS /api/v1, /privacy, and /support URL values plus a valid VITE_SUPPORT_EMAIL in the release environment.",
  "Create a dedicated store-review account and replace STORE_REVIEW_ACCOUNT_EMAIL with its valid email.",
  "Configure EAS production environment variables and signing credentials.",
  "Create cml-memoryhive-mobile/builds/eas-release-evidence.json from the example after EAS project, environment, and signing setup are complete.",
  "Create Apple Developer and Google Play app records.",
  "Produce a signed iOS .ipa and record it in cml-memoryhive-mobile/builds/native-artifacts.json.",
  "Produce a signed Android .aab or .apk and record it in cml-memoryhive-mobile/builds/native-artifacts.json.",
  "Record native-device test evidence for iOS and Android in cml-memoryhive-mobile/builds/native-artifacts.json.",
  "Verify Android targetSdkVersion >= 36 and RECORD_AUDIO absence from the final merged manifest.",
  "Complete Apple App Privacy and Google Play Data safety forms from verified production behavior.",
  "Create cml-memoryhive-mobile/store-assets/store-console-evidence.json from the example after App Store Connect and Play Console fields are complete.",
  "Replace Expo-web screenshots with native-device captures after signed builds if native UI differs or store review requires native screenshots.",
];

const packet = {
  generator: "cml-memoryhive-mobile/scripts/generate-store-submission.mjs",
  status: "draft",
  app: {
    name: appConfig.name,
    slug: appConfig.slug,
    version: appConfig.version,
    scheme: appConfig.scheme,
    ios_bundle_identifier: appConfig.ios?.bundleIdentifier,
    ios_build_number: appConfig.ios?.buildNumber,
    android_package: appConfig.android?.package,
    android_version_code: appConfig.android?.versionCode,
    category: "Productivity",
  },
  urls: productionUrls,
  contacts: productionContacts,
  copy,
  assets: {
    icon_source: icon,
    google_play_feature_graphic: featureGraphic,
    screenshots,
  },
  app_store: {
    subtitle: copy.app_store_subtitle,
    promotional_text: copy.promotional_text,
    privacy_policy_url: productionUrls.privacy_policy_url,
    support_url: productionUrls.support_url,
    review_account: {
      email: storeReviewAccountEmail,
      password: "Do not commit. Generate a temporary password and enter it directly in App Store Connect.",
      notes: "Mention offline mode, share intent, account export, and account deletion paths.",
    },
    privacy_draft: privacyDraft,
  },
  google_play: {
    short_description: copy.google_play_short_description,
    full_description: `${copy.full_description}\n\nKey features:\n${copy.features.map((feature) => `- ${feature}`).join("\n")}`,
    privacy_policy_url: productionUrls.privacy_policy_url,
    account_deletion_url: productionUrls.account_deletion_url,
    review_account: {
      email: storeReviewAccountEmail,
      password: "Do not commit. Generate a temporary password and enter it directly in Play Console.",
      notes: "Use the same reviewer account as App Store Connect when possible.",
    },
    data_safety_draft: privacyDraft,
  },
  release_blockers: releaseBlockers,
};

const markdown = `# Mobile Store Submission Packet

Status: draft handoff generated from \`npm run store:submission\`.

## App Identity

| Field | Value |
| --- | --- |
| Name | ${packet.app.name} |
| Version | ${packet.app.version} |
| iOS bundle ID | \`${packet.app.ios_bundle_identifier}\` |
| Android package | \`${packet.app.android_package}\` |
| Category | ${packet.app.category} |
| Privacy URL | ${packet.urls.privacy_policy_url} |
| Support URL | ${packet.urls.support_url} |
| Account deletion URL | ${packet.urls.account_deletion_url} |
| Support email | ${packet.contacts.support_email} |

## Store Copy

App Store subtitle:

> ${copy.app_store_subtitle}

Google Play short description:

> ${copy.google_play_short_description}

Promotional text:

> ${copy.promotional_text}

Full description:

${copy.full_description}

Key features:

${markdownList(copy.features)}

Keywords:

${copy.keywords}

## Assets

- Store icon: \`${icon.path}\` (${icon.dimensions}) - ${icon.alt_text}
- Google Play feature graphic: \`${featureGraphic.path}\` (${featureGraphic.dimensions}) - ${featureGraphic.alt_text}

Screenshots:

${markdownList(screenshots.map((asset) => `\`${asset.name}\` (${asset.platform} ${asset.form_factor}, ${asset.dimensions}) - ${asset.alt_text}`))}

## Privacy And Data Safety

Apple data types:

${markdownList(privacyDraft.apple_data_types)}

Google data categories:

${markdownList(privacyDraft.google_data_categories)}

Tracking: ${privacyDraft.tracking}

Security: ${privacyDraft.security}

External AI processing: ${privacyDraft.external_ai_processing.mode}

${privacyDraft.external_ai_processing.notes}

Production telemetry: ${privacyDraft.production_telemetry.mode}

${privacyDraft.production_telemetry.notes}

## Review Access

App Store Connect:

- Email: \`${packet.app_store.review_account.email}\`
- Password: ${packet.app_store.review_account.password}
- Notes: ${packet.app_store.review_account.notes}

Play Console:

- Email: \`${packet.google_play.review_account.email}\`
- Password: ${packet.google_play.review_account.password}
- Notes: ${packet.google_play.review_account.notes}

## Release Blockers

${markdownList(releaseBlockers)}
`;

const generatedOutputs = [
  {
    content: `${JSON.stringify(packet, null, 2)}\n`,
    filePath: outputJsonPath,
    label: "cml-memoryhive-mobile/store-assets/submission-packet.json",
  },
  {
    content: markdown,
    filePath: outputMarkdownPath,
    label: "docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md",
  },
];

if (checkOnly) {
  const mismatches = generatedOutputMismatches(generatedOutputs, (filePath) => {
    if (!fs.existsSync(filePath)) return undefined;
    return fs.readFileSync(filePath, "utf8");
  });
  if (mismatches.length) {
    console.error("Store submission output is missing or stale:");
    for (const { label } of mismatches) console.error(`- ${label}`);
    console.error("Run npm run store:submission with the same release environment.");
    process.exitCode = 1;
  } else {
    console.log("Store submission packet is current.");
  }
} else {
  for (const { content, filePath, label } of generatedOutputs) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content);
    console.log(`Generated ${label}`);
  }
}
if (releaseEnvFile.path) {
  console.log(`Loaded release env file ${path.relative(repoRoot, releaseEnvFile.path) || releaseEnvFile.path}`);
}
