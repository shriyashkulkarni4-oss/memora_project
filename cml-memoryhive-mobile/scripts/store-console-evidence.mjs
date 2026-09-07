export const storeConsoleEvidencePath = "cml-memoryhive-mobile/store-assets/store-console-evidence.json";
export const storeConsoleEvidenceTemplatePath =
  "cml-memoryhive-mobile/store-assets/store-console-evidence.example.json";

const iosBundleIdentifier = "com.codingmonkeylabs.memoryhive";
const androidPackageName = "com.codingmonkeylabs.memoryhive";

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isTrue(value) {
  return value === true;
}

function isPlaceholderText(value) {
  return !hasText(value) || /replace|example|todo|tbd|placeholder/i.test(value);
}

function isIsoTimestamp(value) {
  return (
    hasText(value) &&
    /^\d{4}-\d{2}-\d{2}T/.test(value) &&
    !Number.isNaN(Date.parse(value))
  );
}

export function appStoreConsoleEvidenceReady(evidence, releaseConfig) {
  const appStore = evidence?.app_store_connect;
  return Boolean(
    isTrue(appStore?.app_record_created) &&
      appStore?.bundle_identifier === iosBundleIdentifier &&
      appStore?.privacy_policy_url === releaseConfig.urls.privacy_policy_url &&
      appStore?.support_url === releaseConfig.urls.support_url &&
      appStore?.review_account_email === releaseConfig.reviewAccountEmail &&
      isTrue(appStore?.store_listing_completed) &&
      isTrue(appStore?.screenshots_uploaded) &&
      isTrue(appStore?.app_privacy_completed) &&
      isTrue(appStore?.age_rating_completed) &&
      isTrue(appStore?.export_compliance_completed) &&
      isTrue(appStore?.review_information_completed),
  );
}

export function googlePlayConsoleEvidenceReady(evidence, releaseConfig) {
  const googlePlay = evidence?.google_play_console;
  return Boolean(
    isTrue(googlePlay?.app_record_created) &&
      googlePlay?.package_name === androidPackageName &&
      googlePlay?.privacy_policy_url === releaseConfig.urls.privacy_policy_url &&
      googlePlay?.account_deletion_url === releaseConfig.urls.account_deletion_url &&
      googlePlay?.support_email === releaseConfig.contacts.support_email &&
      googlePlay?.review_account_email === releaseConfig.reviewAccountEmail &&
      isTrue(googlePlay?.store_listing_completed) &&
      isTrue(googlePlay?.feature_graphic_uploaded) &&
      isTrue(googlePlay?.screenshots_uploaded) &&
      isTrue(googlePlay?.data_safety_completed) &&
      isTrue(googlePlay?.content_rating_completed) &&
      isTrue(googlePlay?.target_audience_completed) &&
      isTrue(googlePlay?.app_access_completed),
  );
}

export function finalPrivacyEvidenceReady(evidence, releaseConfig) {
  const privacy = evidence?.privacy_verification;
  return Boolean(
    !isPlaceholderText(privacy?.verified_by) &&
      isIsoTimestamp(privacy?.verified_at) &&
      privacy?.external_ai_processing ===
        releaseConfig.privacyDisclosures.external_ai_processing.mode &&
      privacy?.production_telemetry ===
        releaseConfig.privacyDisclosures.production_telemetry.mode &&
      isTrue(privacy?.retention_review_completed) &&
      isTrue(privacy?.deletion_flow_verified),
  );
}

export function storeConsoleEvidenceReady(evidence, releaseConfig) {
  return Boolean(
    appStoreConsoleEvidenceReady(evidence, releaseConfig) &&
      googlePlayConsoleEvidenceReady(evidence, releaseConfig) &&
      finalPrivacyEvidenceReady(evidence, releaseConfig),
  );
}
