#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  assertNoNativeEnvFileFlag,
  loadStoreEnvFile,
  parseStoreScriptArgs,
} from "./store-env.mjs";
import {
  androidArtifactExtensions,
  androidBuildEvidenceReady,
  androidTargetSdkMinimum,
  iosArtifactExtensions,
  iosBuildEvidenceReady,
  nativeArtifactManifestPath,
  recordedArtifactExists,
  testedDeviceCount,
} from "./native-build-evidence.mjs";
import {
  easAndroidCredentialsEvidenceReady,
  easBuildProfilesReady,
  easCliConfigReady,
  easIosCredentialsEvidenceReady,
  easProductionEnvironmentEvidenceReady,
  easProjectIdentityReady,
  easReleaseEvidencePath,
  easReleaseEvidenceTemplatePath,
  easSubmitProfileReady,
} from "./eas-release-readiness.mjs";
import {
  isExternalAiDisclosureConsistent,
  isKnownPrivacyDisclosureValue,
  isProductionEmail,
  isProductionHttpsUrl,
  privacyDisclosureSpecs,
  productionEnvTemplatePath,
  productionUrlSpecs,
  resolveStoreReleaseConfig,
} from "./store-release-config.mjs";
import {
  appStoreSubtitleLength,
  appStoreSubtitleLimit,
  appStoreSubtitleWithinLimit,
  googlePlayShortDescriptionLength,
  googlePlayShortDescriptionLimit,
  googlePlayShortDescriptionWithinLimit,
  submissionPacketHasRequiredFields,
  submissionPacketKeepsReviewPasswordsOutOfSource,
  submissionPacketMatchesReleaseConfig,
} from "./store-submission-packet.mjs";
import {
  appStoreConsoleEvidenceReady,
  finalPrivacyEvidenceReady,
  googlePlayConsoleEvidenceReady,
  storeConsoleEvidencePath,
  storeConsoleEvidenceTemplatePath,
} from "./store-console-evidence.mjs";
import {
  expectedStoreScreenshots,
  invalidExpectedScreenshots,
  isFeatureGraphicReady,
  isStoreIconReady,
  missingExpectedScreenshots,
  pngMetadataFromBuffer,
  screenshotManifestHasMetadata,
  storeAssetManifestHasMetadata,
} from "./store-asset-readiness.mjs";
import {
  blockerScope,
  readinessShouldFail,
  summarizeReadinessResults,
} from "./store-readiness-results.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const mobileRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(mobileRoot, "..");
let cliOptions;
let releaseEnvFile;
try {
  assertNoNativeEnvFileFlag(process.execArgv);
  cliOptions = parseStoreScriptArgs(process.argv.slice(2));
  releaseEnvFile = loadStoreEnvFile(cliOptions.envFilePath, { repoRoot });
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
const strict = cliOptions.remainingArgs.includes("--strict");
const ci = cliOptions.remainingArgs.includes("--ci");

const results = [];

function repoPath(relativePath) {
  return path.join(repoRoot, relativePath);
}

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(repoPath(relativePath), "utf8"));
}

function readJsonIfExists(relativePath) {
  if (!exists(relativePath)) return null;
  try {
    return readJson(relativePath);
  } catch {
    return null;
  }
}

function readText(relativePath) {
  return fs.readFileSync(repoPath(relativePath), "utf8");
}

function exists(relativePath) {
  return fs.existsSync(repoPath(relativePath));
}

function fileHasContent(relativePath) {
  try {
    const stats = fs.statSync(repoPath(relativePath));
    return stats.isFile() && stats.size > 0;
  } catch {
    return false;
  }
}

function result(level, title, detail, scope) {
  results.push({ level, title, detail, scope });
}

function pass(title, detail) {
  result("OK", title, detail);
}

function warn(title, detail) {
  result("WARN", title, detail);
}

function block(title, detail, scope = blockerScope.repository) {
  result("BLOCKED", title, detail, scope);
}

function check(
  condition,
  title,
  passDetail,
  blockDetail,
  scope = blockerScope.repository,
) {
  if (condition) pass(title, passDetail);
  else block(title, blockDetail, scope);
}

function envValue(relativePath, name) {
  const match = readText(relativePath).match(new RegExp(`^${name}=(.*)$`, "m"));
  return match?.[1]?.trim();
}

function pngSize(relativePath) {
  if (!exists(relativePath)) return null;
  const buffer = fs.readFileSync(repoPath(relativePath));
  return pngMetadataFromBuffer(buffer);
}

function findFiles(relativePath, extensions) {
  if (!exists(relativePath)) return [];
  return fs
    .readdirSync(repoPath(relativePath), { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter((name) => extensions.includes(path.extname(name).toLowerCase()));
}

const appConfig = readJson("mobile/app.json").expo;
const easConfig = readJson("mobile/eas.json");
const appRoutes = readText("frontend/src/App.tsx");
const releaseWorkflow = exists(".github/workflows/release.yml")
  ? readText(".github/workflows/release.yml")
  : "";
const frontendConfig = exists("frontend/src/config.ts") ? readText("frontend/src/config.ts") : "";
const accountDeletionPage = exists("frontend/src/components/AccountDeletionPage.tsx")
  ? readText("frontend/src/components/AccountDeletionPage.tsx")
  : "";
const privacyPage = exists("frontend/src/components/PrivacyPage.tsx")
  ? readText("frontend/src/components/PrivacyPage.tsx")
  : "";
const supportPage = exists("frontend/src/components/SupportPage.tsx")
  ? readText("frontend/src/components/SupportPage.tsx")
  : "";
const releaseConfig = resolveStoreReleaseConfig({
  readTemplateValue: envValue,
  envFile: releaseEnvFile,
});

check(
  appConfig.ios?.bundleIdentifier === "com.codingmonkeylabs.memoryhive",
  "iOS bundle ID",
  "com.codingmonkeylabs.memoryhive",
  "Set ios.bundleIdentifier to com.codingmonkeylabs.memoryhive.",
);
check(
  appConfig.android?.package === "com.codingmonkeylabs.memoryhive",
  "Android package",
  "com.codingmonkeylabs.memoryhive",
  "Set android.package to com.codingmonkeylabs.memoryhive.",
);
check(
  appConfig.android?.blockedPermissions?.includes("android.permission.RECORD_AUDIO"),
  "Android sensitive permission review",
  "RECORD_AUDIO is blocked.",
  "Block RECORD_AUDIO unless the app adds microphone capture.",
);
check(
  easProjectIdentityReady(appConfig),
  "EAS project identity",
  `Project ID ${appConfig.extra?.eas?.projectId}`,
  "Run npx eas-cli@latest init and commit extra.eas.projectId.",
  blockerScope.release,
);
check(
  easCliConfigReady(easConfig),
  "EAS CLI config",
  "EAS CLI version and remote app-version source are configured.",
  "Set eas.json cli.version to >= 16 and cli.appVersionSource to remote.",
);
check(
  easBuildProfilesReady(easConfig),
  "EAS build profiles",
  "development, preview, and production profiles are release-aligned.",
  "Define internal development/preview profiles and production auto-increment/channel in mobile/eas.json.",
);
check(
  easSubmitProfileReady(easConfig),
  "EAS submit profile",
  "production submit profile exists.",
  "Define submit.production in mobile/eas.json.",
);
if (releaseEnvFile.path) {
  pass("Release env file", `Loaded ${path.relative(repoRoot, releaseEnvFile.path) || releaseEnvFile.path}.`);
}

for (const { name, title, requiredPath, detail } of productionUrlSpecs) {
  check(
    envValue(".env.example", name) !== undefined,
    `.env.example ${name}`,
    "Documented.",
    `Add ${name} to .env.example.`,
  );
  const productionValue = envValue(productionEnvTemplatePath, name);
  check(
    Boolean(productionValue),
    `.env.production.example ${name}`,
    "Documented with a production placeholder.",
    `Add ${name} to .env.production.example.`,
  );
  check(
    isProductionHttpsUrl(releaseConfig.values[name], requiredPath),
    title,
    "Configured with a public non-placeholder HTTPS value.",
    detail,
    blockerScope.release,
  );
}
check(
  envValue(".env.example", "VITE_SUPPORT_EMAIL") !== undefined,
  ".env.example VITE_SUPPORT_EMAIL",
  "Documented.",
  "Add VITE_SUPPORT_EMAIL to .env.example.",
);
const productionSupportEmailTemplate = envValue(productionEnvTemplatePath, "VITE_SUPPORT_EMAIL");
const productionSupportEmail = releaseConfig.contacts.support_email;
check(
  Boolean(productionSupportEmailTemplate),
  ".env.production.example VITE_SUPPORT_EMAIL",
  "Documented with a production placeholder.",
  "Add VITE_SUPPORT_EMAIL to .env.production.example.",
);
check(
  releaseWorkflow.includes("vars.VITE_SUPPORT_EMAIL") &&
    !releaseWorkflow.includes("VITE_SUPPORT_EMAIL=support@memoryhive.example.com"),
  "Release frontend support email",
  "Release workflow injects VITE_SUPPORT_EMAIL from a repository variable.",
  "Update .github/workflows/release.yml to inject VITE_SUPPORT_EMAIL from a repository variable instead of a placeholder.",
);

for (const route of ["/privacy", "/account/delete", "/support"]) {
  check(
    appRoutes.includes(`path="${route}"`),
    `Public route ${route}`,
    "Routed in the web app.",
    `Add a public React route for ${route}.`,
  );
}
check(
  frontendConfig.includes("VITE_SUPPORT_EMAIL") &&
    [accountDeletionPage, privacyPage, supportPage].every((source) => source.includes("SUPPORT_MAILTO")),
  "Support contact links",
  "Public compliance pages use the configured support email.",
  "Wire VITE_SUPPORT_EMAIL through every public compliance page mailto link.",
);
check(
  isProductionEmail(productionSupportEmail),
  "Real support contact",
  "VITE_SUPPORT_EMAIL is configured with a syntactically valid non-placeholder address.",
  "Replace VITE_SUPPORT_EMAIL with the operator's real support address before submission.",
  blockerScope.release,
);
check(
  envValue(".env.example", "STORE_REVIEW_ACCOUNT_EMAIL") !== undefined,
  ".env.example STORE_REVIEW_ACCOUNT_EMAIL",
  "Documented.",
  "Add STORE_REVIEW_ACCOUNT_EMAIL to .env.example.",
);
const productionReviewAccountEmailTemplate = envValue(
  productionEnvTemplatePath,
  "STORE_REVIEW_ACCOUNT_EMAIL",
);
const productionReviewAccountEmail = releaseConfig.reviewAccountEmail;
check(
  Boolean(productionReviewAccountEmailTemplate),
  ".env.production.example STORE_REVIEW_ACCOUNT_EMAIL",
  "Documented with a production placeholder.",
  "Add STORE_REVIEW_ACCOUNT_EMAIL to .env.production.example.",
);
check(
  isProductionEmail(productionReviewAccountEmail),
  "Store review account",
  "STORE_REVIEW_ACCOUNT_EMAIL is configured with a syntactically valid non-placeholder address.",
  "Create a dedicated reviewer account, set STORE_REVIEW_ACCOUNT_EMAIL to its real email, and enter its temporary password directly in App Store Connect and Play Console.",
  blockerScope.release,
);

for (const { name, title, detail } of privacyDisclosureSpecs) {
  check(
    envValue(".env.example", name) !== undefined,
    `.env.example ${name}`,
    "Documented.",
    `Add ${name} to .env.example.`,
  );
  check(
    envValue(productionEnvTemplatePath, name) !== undefined,
    `.env.production.example ${name}`,
    "Documented with a production disclosure value.",
    `Add ${name} to .env.production.example.`,
  );
  check(
    isKnownPrivacyDisclosureValue(name, releaseConfig.values[name]),
    title,
    `${name}=${releaseConfig.values[name]}.`,
    detail,
  );
}
check(
  isExternalAiDisclosureConsistent(releaseConfig),
  "External AI disclosure consistency",
  "External AI disclosure is aligned with configured backend enrichment endpoints.",
  "Backend enrichment endpoints are configured; set STORE_EXTERNAL_AI_PROCESSING to self_hosted or third_party before submission.",
);

for (const doc of [
  "docs/GOAL-1/MOBILE_IOS_BUILD_TEST.md",
  "docs/GOAL-1/MOBILE_ANDROID_BUILD_TEST.md",
  "docs/GOAL-1/MOBILE_APP_STORE_READINESS.md",
  "docs/GOAL-1/MOBILE_STORE_METADATA.md",
  "docs/GOAL-1/MOBILE_PRIVACY_DATA_SAFETY.md",
  "docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md",
]) {
  check(exists(doc), doc, "Present.", "Create this release document.");
}

const appIcon = pngSize("mobile/assets/images/icon.png");
const storeIcon = pngSize("mobile/store-assets/icon-1024.png");
const icon = storeIcon ?? appIcon;
check(
  isStoreIconReady(icon),
  "Store icon source",
  `Store icon source is ${icon?.width}x${icon?.height} RGB PNG.`,
  `Run npm run store:assets or provide mobile/store-assets/icon-1024.png as a 1024x1024 RGB PNG; current app icon is ${appIcon?.width ?? "missing"}x${appIcon?.height ?? "missing"}.`,
);
const featureGraphic = pngSize("mobile/store-assets/feature-graphic.png");
check(
  isFeatureGraphicReady(featureGraphic),
  "Google Play feature graphic",
  "mobile/store-assets/feature-graphic.png is 1024x500 RGB PNG.",
  "Run npm run store:assets or provide mobile/store-assets/feature-graphic.png as a 1024x500 RGB PNG.",
);
const assetManifest = readJsonIfExists("mobile/store-assets/manifest.json");
check(
  storeAssetManifestHasMetadata(assetManifest),
  "Store asset metadata",
  "Asset manifest includes dimensions, purpose, and alt text.",
  "Run npm run store:assets to regenerate mobile/store-assets/manifest.json with release metadata.",
);
const screenshots = findFiles("mobile/store-assets/screenshots", [".png", ".jpg", ".jpeg"]);
const screenshotMetadataFor = (name) => pngSize(`mobile/store-assets/screenshots/${name}`);
const missingScreenshots = missingExpectedScreenshots(screenshots);
const invalidScreenshots = invalidExpectedScreenshots({
  fileNames: screenshots,
  pngMetadataFor: screenshotMetadataFor,
});
check(
  missingScreenshots.length === 0 && invalidScreenshots.length === 0,
  "Store screenshots",
  `${expectedStoreScreenshots.length} expected store-size RGB screenshot assets found.`,
  `Run npm run store:screenshots with the local backend running; missing ${missingScreenshots.map((screenshot) => screenshot.name).join(", ") || "none"}, invalid ${invalidScreenshots.map((screenshot) => screenshot.name).join(", ") || "none"}.`,
);
const screenshotManifest = readJsonIfExists("mobile/store-assets/screenshots/manifest.json");
check(
  screenshotManifestHasMetadata(screenshotManifest),
  "Store screenshot metadata",
  "Screenshot manifest includes platform, form factor, dimensions, screen, and alt text.",
  "Run npm run store:screenshots to regenerate mobile/store-assets/screenshots/manifest.json with release metadata.",
);
const submissionPacket = readJsonIfExists("mobile/store-assets/submission-packet.json");
check(
  submissionPacketHasRequiredFields(submissionPacket, expectedStoreScreenshots.length),
  "Store submission packet",
  "Submission packet includes app identity, copy, privacy draft, assets, screenshots, and blockers.",
  "Run npm run store:submission to regenerate mobile/store-assets/submission-packet.json and docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md.",
);
check(
  submissionPacketMatchesReleaseConfig(submissionPacket, releaseConfig),
  "Store submission packet release config",
  "Submission packet matches configured production URLs, contacts, reviewer email, and privacy disclosures.",
  "Run npm run store:submission with the same release environment used for npm run store:check.",
);
check(
  submissionPacketKeepsReviewPasswordsOutOfSource(submissionPacket),
  "Store review password handling",
  "Reviewer passwords are documented as out-of-band store-console entries.",
  "Do not commit reviewer passwords; regenerate the submission packet so password fields contain out-of-band instructions.",
);
check(
  appStoreSubtitleWithinLimit(submissionPacket),
  "App Store subtitle length",
  `${appStoreSubtitleLength(submissionPacket)}/${appStoreSubtitleLimit} characters.`,
  `Set app_store.subtitle in the submission packet to ${appStoreSubtitleLimit} characters or fewer.`,
);
check(
  googlePlayShortDescriptionWithinLimit(submissionPacket),
  "Google Play short description length",
  `${googlePlayShortDescriptionLength(submissionPacket)}/${googlePlayShortDescriptionLimit} characters.`,
  `Set google_play.short_description in the submission packet to ${googlePlayShortDescriptionLimit} characters or fewer.`,
);
check(
  exists("mobile/builds/native-artifacts.example.json"),
  "Native build evidence template",
  "mobile/builds/native-artifacts.example.json documents required release evidence.",
  "Add a native build evidence manifest template under mobile/builds/.",
);
check(
  exists(easReleaseEvidenceTemplatePath),
  "EAS release evidence template",
  `${easReleaseEvidenceTemplatePath} documents required EAS environment and signing evidence.`,
  `Add ${easReleaseEvidenceTemplatePath} with EAS project, environment, iOS signing, and Android signing fields.`,
);
const easReleaseEvidence = readJsonIfExists(easReleaseEvidencePath);
check(
  easProductionEnvironmentEvidenceReady(easReleaseEvidence, releaseConfig, appConfig),
  "EAS production environment evidence",
  "EAS project ID and production public environment variables are recorded.",
  `Create ${easReleaseEvidencePath} from ${easReleaseEvidenceTemplatePath} after EAS init and production environment configuration.`,
  blockerScope.release,
);
check(
  easIosCredentialsEvidenceReady(easReleaseEvidence),
  "EAS iOS signing evidence",
  "iOS signing credentials, Apple team, production profile, and submit setup are recorded.",
  `Record iOS signing and submit setup in ${easReleaseEvidencePath} after EAS credentials are configured.`,
  blockerScope.release,
);
check(
  easAndroidCredentialsEvidenceReady(easReleaseEvidence),
  "EAS Android signing evidence",
  "Android keystore, Play app signing, service account, and submit setup are recorded.",
  `Record Android signing and submit setup in ${easReleaseEvidencePath} after EAS credentials are configured.`,
  blockerScope.release,
);
check(
  exists(storeConsoleEvidenceTemplatePath),
  "Store console evidence template",
  `${storeConsoleEvidenceTemplatePath} documents required App Store and Play Console evidence.`,
  `Add ${storeConsoleEvidenceTemplatePath} with App Store, Play Console, and privacy verification fields.`,
);
const storeConsoleEvidence = readJsonIfExists(storeConsoleEvidencePath);
check(
  appStoreConsoleEvidenceReady(storeConsoleEvidence, releaseConfig),
  "App Store Connect evidence",
  "App record, listing, screenshots, privacy, age rating, export compliance, and review info are recorded.",
  `Create ${storeConsoleEvidencePath} from ${storeConsoleEvidenceTemplatePath} after completing App Store Connect fields; keep reviewer passwords out of source.`,
  blockerScope.release,
);
check(
  googlePlayConsoleEvidenceReady(storeConsoleEvidence, releaseConfig),
  "Google Play Console evidence",
  "App record, listing, feature graphic, screenshots, Data safety, content rating, target audience, and app access are recorded.",
  `Create ${storeConsoleEvidencePath} from ${storeConsoleEvidenceTemplatePath} after completing Play Console fields; keep reviewer passwords out of source.`,
  blockerScope.release,
);
check(
  finalPrivacyEvidenceReady(storeConsoleEvidence, releaseConfig),
  "Final privacy form evidence",
  "Production disclosure values, retention review, and deletion-flow verification are recorded.",
  `Record product/legal/operations verification in ${storeConsoleEvidencePath} with disclosure values matching the release environment.`,
  blockerScope.release,
);
const nativeArtifactManifest = readJsonIfExists(nativeArtifactManifestPath);
const iosBuildEvidence = nativeArtifactManifest?.ios;
const androidBuildEvidence = nativeArtifactManifest?.android;
const iosArtifacts = [
  ...findFiles("mobile/builds", [".ipa"]).map((name) => `mobile/builds/${name}`),
  ...findFiles("mobile", [".ipa"]).map((name) => `mobile/${name}`),
].filter(fileHasContent);
const androidArtifacts = [
  ...findFiles("mobile/builds", [".aab", ".apk"]).map((name) => `mobile/builds/${name}`),
  ...findFiles("mobile", [".aab", ".apk"]).map((name) => `mobile/${name}`),
].filter(fileHasContent);
const nativeEvidenceContext = { repoRoot, fileHasContent };
const iosRecordedArtifactPresent = recordedArtifactExists(
  iosBuildEvidence?.artifact_path,
  iosArtifactExtensions,
  nativeEvidenceContext,
);
const androidRecordedArtifactPresent = recordedArtifactExists(
  androidBuildEvidence?.artifact_path,
  androidArtifactExtensions,
  nativeEvidenceContext,
);
const iosArtifactPresent = iosArtifacts.length > 0 || iosRecordedArtifactPresent;
const androidArtifactPresent =
  androidArtifacts.length > 0 || androidRecordedArtifactPresent;
check(
  iosArtifactPresent,
  "Signed iOS build artifact",
  iosBuildEvidence?.artifact_path
    ? `Recorded ${iosBuildEvidence.artifact_path}.`
    : `${iosArtifacts.length} .ipa artifact(s) found.`,
  `Produce a signed iOS .ipa and record a non-empty path under mobile/builds/ in ${nativeArtifactManifestPath}.`,
  blockerScope.release,
);
check(
  androidArtifactPresent,
  "Signed Android build artifact",
  androidBuildEvidence?.artifact_path
    ? `Recorded ${androidBuildEvidence.artifact_path}.`
    : `${androidArtifacts.length} .aab/.apk artifact(s) found.`,
  `Produce a signed Android .aab or .apk and record a non-empty path under mobile/builds/ in ${nativeArtifactManifestPath}.`,
  blockerScope.release,
);
check(
  iosBuildEvidenceReady(iosBuildEvidence, nativeEvidenceContext),
  "iOS build test evidence",
  `${testedDeviceCount(iosBuildEvidence?.tested_devices)} iOS device test record(s).`,
  `Create ${nativeArtifactManifestPath} from the example and record production iOS build ID, a non-empty .ipa path under mobile/builds/, and at least two tested iPhone/iPad devices.`,
  blockerScope.release,
);
check(
  androidBuildEvidenceReady(androidBuildEvidence, nativeEvidenceContext),
  "Android target and permission evidence",
  `targetSdkVersion ${androidBuildEvidence?.target_sdk_version}; RECORD_AUDIO present: ${androidBuildEvidence?.record_audio_permission_present}.`,
  `Record production Android build ID, a non-empty .aab/.apk path under mobile/builds/, targetSdkVersion >= ${androidTargetSdkMinimum}, RECORD_AUDIO absence, and at least two tested Android devices in ${nativeArtifactManifestPath}.`,
  blockerScope.release,
);

console.log("Memoryhive mobile store readiness\n");
for (const entry of results) {
  const scope = entry.level === "BLOCKED" ? ` [${entry.scope}]` : "";
  console.log(`${entry.level.padEnd(7)}${scope} ${entry.title}: ${entry.detail}`);
}

const counts = summarizeReadinessResults(results);
console.log(
  `\nSummary: ${counts.ok} ok, ${counts.warnings} warning(s), ${counts.blockers} blocker(s).`,
);
console.log(
  `Blockers: ${counts.repositoryBlockers} repository, ${counts.releaseBlockers} release.`,
);
if (readinessShouldFail({ counts, ci, strict })) process.exitCode = 1;
