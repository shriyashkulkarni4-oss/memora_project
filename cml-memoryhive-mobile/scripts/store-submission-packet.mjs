export const appStoreSubtitleLimit = 30;
export const googlePlayShortDescriptionLimit = 80;

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function submissionPacketHasRequiredFields(packet, expectedScreenshotCount) {
  return Boolean(
    packet?.app?.ios_bundle_identifier === "com.codingmonkeylabs.memoryhive" &&
      packet?.app?.android_package === "com.codingmonkeylabs.memoryhive" &&
      hasText(packet?.copy?.app_store_subtitle) &&
      hasText(packet?.copy?.google_play_short_description) &&
      hasText(packet?.contacts?.support_email) &&
      packet?.app_store?.privacy_draft?.external_ai_processing &&
      packet?.app_store?.privacy_draft?.production_telemetry &&
      hasText(packet?.app_store?.review_account?.email) &&
      hasText(packet?.google_play?.review_account?.email) &&
      packet?.google_play?.data_safety_draft?.external_ai_processing &&
      packet?.google_play?.data_safety_draft?.production_telemetry &&
      hasText(packet?.assets?.icon_source?.path) &&
      hasText(packet?.assets?.google_play_feature_graphic?.path) &&
      packet?.assets?.screenshots?.length >= expectedScreenshotCount &&
      packet?.release_blockers?.length,
  );
}

export function submissionPacketMatchesReleaseConfig(packet, releaseConfig) {
  return Boolean(
    packet?.urls?.api_url === releaseConfig.urls.api_url &&
      packet?.urls?.support_url === releaseConfig.urls.support_url &&
      packet?.urls?.privacy_policy_url === releaseConfig.urls.privacy_policy_url &&
      packet?.urls?.account_deletion_url === releaseConfig.urls.account_deletion_url &&
      packet?.contacts?.support_email === releaseConfig.contacts.support_email &&
      packet?.app_store?.review_account?.email === releaseConfig.reviewAccountEmail &&
      packet?.google_play?.review_account?.email === releaseConfig.reviewAccountEmail &&
      packet?.app_store?.privacy_draft?.external_ai_processing?.mode ===
        releaseConfig.privacyDisclosures.external_ai_processing.mode &&
      packet?.google_play?.data_safety_draft?.external_ai_processing?.mode ===
        releaseConfig.privacyDisclosures.external_ai_processing.mode &&
      packet?.app_store?.privacy_draft?.production_telemetry?.mode ===
        releaseConfig.privacyDisclosures.production_telemetry.mode &&
      packet?.google_play?.data_safety_draft?.production_telemetry?.mode ===
        releaseConfig.privacyDisclosures.production_telemetry.mode,
  );
}

function isOutOfBandPasswordInstruction(value) {
  return (
    typeof value === "string" &&
    value.includes("Do not commit.") &&
    value.includes("directly in")
  );
}

export function submissionPacketKeepsReviewPasswordsOutOfSource(packet) {
  return Boolean(
    isOutOfBandPasswordInstruction(packet?.app_store?.review_account?.password) &&
      isOutOfBandPasswordInstruction(packet?.google_play?.review_account?.password),
  );
}

export function appStoreSubtitleLength(packet) {
  return packet?.app_store?.subtitle?.length ?? 0;
}

export function googlePlayShortDescriptionLength(packet) {
  return packet?.google_play?.short_description?.length ?? 0;
}

export function appStoreSubtitleWithinLimit(packet) {
  return Boolean(
    hasText(packet?.app_store?.subtitle) &&
      appStoreSubtitleLength(packet) <= appStoreSubtitleLimit,
  );
}

export function googlePlayShortDescriptionWithinLimit(packet) {
  return Boolean(
    hasText(packet?.google_play?.short_description) &&
      googlePlayShortDescriptionLength(packet) <= googlePlayShortDescriptionLimit,
  );
}
