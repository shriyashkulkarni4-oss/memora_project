import { describe, expect, it } from "vitest";

import {
  appStoreConsoleEvidenceReady,
  finalPrivacyEvidenceReady,
  googlePlayConsoleEvidenceReady,
  storeConsoleEvidenceReady,
} from "../scripts/store-console-evidence.mjs";

const releaseConfig = {
  urls: {
    privacy_policy_url: "https://app.memoryhive.io/privacy",
    support_url: "https://app.memoryhive.io/support",
    account_deletion_url: "https://app.memoryhive.io/account/delete",
  },
  contacts: {
    support_email: "support@memoryhive.io",
  },
  reviewAccountEmail: "reviewer@memoryhive.io",
  privacyDisclosures: {
    external_ai_processing: { mode: "third_party" },
    production_telemetry: { mode: "crash_reporting" },
  },
};

function evidence(overrides = {}) {
  const base = {
    app_store_connect: {
      app_record_created: true,
      bundle_identifier: "com.codingmonkeylabs.memoryhive",
      privacy_policy_url: releaseConfig.urls.privacy_policy_url,
      support_url: releaseConfig.urls.support_url,
      review_account_email: releaseConfig.reviewAccountEmail,
      store_listing_completed: true,
      screenshots_uploaded: true,
      app_privacy_completed: true,
      age_rating_completed: true,
      export_compliance_completed: true,
      review_information_completed: true,
    },
    google_play_console: {
      app_record_created: true,
      package_name: "com.codingmonkeylabs.memoryhive",
      privacy_policy_url: releaseConfig.urls.privacy_policy_url,
      account_deletion_url: releaseConfig.urls.account_deletion_url,
      support_email: releaseConfig.contacts.support_email,
      review_account_email: releaseConfig.reviewAccountEmail,
      store_listing_completed: true,
      feature_graphic_uploaded: true,
      screenshots_uploaded: true,
      data_safety_completed: true,
      content_rating_completed: true,
      target_audience_completed: true,
      app_access_completed: true,
    },
    privacy_verification: {
      verified_by: "Release Owner",
      verified_at: "2026-09-06T00:00:00.000Z",
      external_ai_processing:
        releaseConfig.privacyDisclosures.external_ai_processing.mode,
      production_telemetry: releaseConfig.privacyDisclosures.production_telemetry.mode,
      retention_review_completed: true,
      deletion_flow_verified: true,
    },
  };
  return {
    ...base,
    ...overrides,
  };
}

describe("store console evidence", () => {
  it("accepts complete App Store, Play Console, and privacy evidence", () => {
    const complete = evidence();

    expect(appStoreConsoleEvidenceReady(complete, releaseConfig)).toBe(true);
    expect(googlePlayConsoleEvidenceReady(complete, releaseConfig)).toBe(true);
    expect(finalPrivacyEvidenceReady(complete, releaseConfig)).toBe(true);
    expect(storeConsoleEvidenceReady(complete, releaseConfig)).toBe(true);
  });

  it("rejects incomplete or stale App Store Connect evidence", () => {
    expect(
      appStoreConsoleEvidenceReady(
        evidence({
          app_store_connect: {
            ...evidence().app_store_connect,
            screenshots_uploaded: false,
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
    expect(
      appStoreConsoleEvidenceReady(
        evidence({
          app_store_connect: {
            ...evidence().app_store_connect,
            support_url: "https://old.memoryhive.io/support",
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
  });

  it("rejects incomplete or stale Google Play Console evidence", () => {
    expect(
      googlePlayConsoleEvidenceReady(
        evidence({
          google_play_console: {
            ...evidence().google_play_console,
            data_safety_completed: false,
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
    expect(
      googlePlayConsoleEvidenceReady(
        evidence({
          google_play_console: {
            ...evidence().google_play_console,
            review_account_email: "reviewer@old.memoryhive.io",
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
  });

  it("rejects unverified or mismatched privacy evidence", () => {
    expect(
      finalPrivacyEvidenceReady(
        evidence({
          privacy_verification: {
            ...evidence().privacy_verification,
            verified_by: "replace-with-owner-name",
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
    expect(
      finalPrivacyEvidenceReady(
        evidence({
          privacy_verification: {
            ...evidence().privacy_verification,
            external_ai_processing: "none",
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
    expect(
      finalPrivacyEvidenceReady(
        evidence({
          privacy_verification: {
            ...evidence().privacy_verification,
            deletion_flow_verified: false,
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
  });
});
