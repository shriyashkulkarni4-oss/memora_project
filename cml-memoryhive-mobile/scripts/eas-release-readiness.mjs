export const easReleaseEvidencePath = "cml-memoryhive-mobile/builds/eas-release-evidence.json";
export const easReleaseEvidenceTemplatePath =
  "cml-memoryhive-mobile/builds/eas-release-evidence.example.json";

export const requiredEasProductionEnvironmentVariables = [
  "EXPO_PUBLIC_API_URL",
  "EXPO_PUBLIC_PRIVACY_POLICY_URL",
  "EXPO_PUBLIC_SUPPORT_URL",
];

const iosBundleIdentifier = "com.codingmonkeylabs.memoryhive";
const androidPackageName = "com.codingmonkeylabs.memoryhive";
const easCliMinimumMajor = 16;

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isTrue(value) {
  return value === true;
}

function isPlaceholderText(value) {
  return !hasText(value) || /replace|example|todo|tbd|placeholder/i.test(value);
}

function isUuid(value) {
  return (
    hasText(value) &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      value,
    )
  );
}

function envNames(values) {
  return Array.isArray(values)
    ? new Set(values.filter(hasText))
    : new Set(Object.keys(values ?? {}).filter(hasText));
}

function cliVersionSpecCoversMinimum(versionSpec) {
  const match = String(versionSpec ?? "").match(/>=\s*(\d+)(?:\.\d+){0,2}/);
  return Boolean(match && Number(match[1]) >= easCliMinimumMajor);
}

export function easProjectIdentityReady(appConfig) {
  return isUuid(appConfig?.extra?.eas?.projectId);
}

export function easCliConfigReady(easConfig) {
  return Boolean(
    cliVersionSpecCoversMinimum(easConfig?.cli?.version) &&
      easConfig?.cli?.appVersionSource === "remote",
  );
}

export function easBuildProfilesReady(easConfig) {
  return Boolean(
    easConfig?.build?.development?.developmentClient === true &&
      easConfig?.build?.development?.distribution === "internal" &&
      easConfig?.build?.development?.environment === "development" &&
      easConfig?.build?.preview?.distribution === "internal" &&
      easConfig?.build?.preview?.channel === "preview" &&
      easConfig?.build?.preview?.environment === "preview" &&
      easConfig?.build?.production?.autoIncrement === true &&
      easConfig?.build?.production?.channel === "production" &&
      easConfig?.build?.production?.environment === "production",
  );
}

export function easCiBuildPreflightErrors({ appConfig, easConfig, expoToken }) {
  const errors = [];
  if (!hasText(expoToken)) {
    errors.push("Set the EXPO_TOKEN GitHub Actions secret.");
  }
  if (!easProjectIdentityReady(appConfig)) {
    errors.push("Run EAS init and commit expo.extra.eas.projectId before queuing builds.");
  }
  if (!easCliConfigReady(easConfig)) {
    errors.push("Configure the EAS CLI version and remote app-version source in eas.json.");
  }
  if (!easBuildProfilesReady(easConfig)) {
    errors.push("Configure development, preview, and production EAS build profiles and environments.");
  }
  return errors;
}

export function easSubmitProfileReady(easConfig) {
  return Boolean(easConfig?.submit?.production);
}

export function easProductionEnvironmentEvidenceReady(
  evidence,
  releaseConfig,
  appConfig,
) {
  const projectId = appConfig?.extra?.eas?.projectId;
  const variableNames = envNames(evidence?.eas?.production_environment_variables);
  return Boolean(
    isUuid(projectId) &&
      evidence?.eas?.project_id === projectId &&
      evidence?.eas?.production_environment === "production" &&
      requiredEasProductionEnvironmentVariables.every((name) => variableNames.has(name)) &&
      releaseConfig?.urls?.api_url &&
      releaseConfig?.urls?.privacy_policy_url &&
      releaseConfig?.urls?.support_url,
  );
}

export function easIosCredentialsEvidenceReady(evidence) {
  const ios = evidence?.ios;
  return Boolean(
    isTrue(ios?.credentials_configured) &&
      ios?.bundle_identifier === iosBundleIdentifier &&
      !isPlaceholderText(ios?.apple_team_id) &&
      isTrue(ios?.production_profile_verified) &&
      isTrue(ios?.submit_profile_configured),
  );
}

export function easAndroidCredentialsEvidenceReady(evidence) {
  const android = evidence?.android;
  return Boolean(
    isTrue(android?.credentials_configured) &&
      android?.package_name === androidPackageName &&
      isTrue(android?.keystore_configured) &&
      isTrue(android?.play_app_signing_enabled) &&
      isTrue(android?.service_account_configured) &&
      isTrue(android?.submit_profile_configured),
  );
}

export function easReleaseEvidenceReady(evidence, releaseConfig, appConfig) {
  return Boolean(
    easProductionEnvironmentEvidenceReady(evidence, releaseConfig, appConfig) &&
      easIosCredentialsEvidenceReady(evidence) &&
      easAndroidCredentialsEvidenceReady(evidence),
  );
}
