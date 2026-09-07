import { describe, expect, it } from "vitest";

import {
  appStoreSubtitleWithinLimit,
  googlePlayShortDescriptionWithinLimit,
  submissionPacketHasRequiredFields,
  submissionPacketKeepsReviewPasswordsOutOfSource,
  submissionPacketMatchesReleaseConfig,
} from "../scripts/store-submission-packet.mjs";

const releaseConfig = {
  urls: {
    api_url: "https://app.memoryhive.io/api/v1",
    support_url: "https://app.memoryhive.io/support",
    privacy_policy_url: "https://app.memoryhive.io/privacy",
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

function packet(overrides = {}) {
  return {
    app: {
      ios_bundle_identifier: "com.codingmonkeylabs.memoryhive",
      android_package: "com.codingmonkeylabs.memoryhive",
    },
    urls: { ...releaseConfig.urls },
    contacts: { ...releaseConfig.contacts },
    copy: {
      app_store_subtitle: "Capture. Tag. Find.",
      google_play_short_description:
        "Capture links, screenshots, and notes into a searchable offline-first library.",
    },
    app_store: {
      subtitle: "Capture. Tag. Find.",
      review_account: {
        email: releaseConfig.reviewAccountEmail,
        password:
          "Do not commit. Generate a temporary password and enter it directly in App Store Connect.",
      },
      privacy_draft: {
        external_ai_processing: { mode: "third_party" },
        production_telemetry: { mode: "crash_reporting" },
      },
    },
    google_play: {
      short_description:
        "Capture links, screenshots, and notes into a searchable offline-first library.",
      review_account: {
        email: releaseConfig.reviewAccountEmail,
        password:
          "Do not commit. Generate a temporary password and enter it directly in Play Console.",
      },
      data_safety_draft: {
        external_ai_processing: { mode: "third_party" },
        production_telemetry: { mode: "crash_reporting" },
      },
    },
    assets: {
      icon_source: { path: "cml-memoryhive-mobile/store-assets/icon-1024.png" },
      google_play_feature_graphic: { path: "cml-memoryhive-mobile/store-assets/feature-graphic.png" },
      screenshots: [{ name: "iphone.png" }, { name: "android.png" }],
    },
    release_blockers: ["Run EAS init."],
    ...overrides,
  };
}

describe("store submission packet validation", () => {
  it("accepts the generated packet shape and release config", () => {
    const candidate = packet();

    expect(submissionPacketHasRequiredFields(candidate, 2)).toBe(true);
    expect(submissionPacketMatchesReleaseConfig(candidate, releaseConfig)).toBe(true);
    expect(submissionPacketKeepsReviewPasswordsOutOfSource(candidate)).toBe(true);
    expect(appStoreSubtitleWithinLimit(candidate)).toBe(true);
    expect(googlePlayShortDescriptionWithinLimit(candidate)).toBe(true);
  });

  it("rejects missing required handoff sections", () => {
    expect(submissionPacketHasRequiredFields(packet({ assets: { screenshots: [] } }), 2)).toBe(
      false,
    );
    expect(
      submissionPacketHasRequiredFields(
        packet({
          app_store: {
            ...packet().app_store,
            privacy_draft: {},
          },
        }),
        2,
      ),
    ).toBe(false);
  });

  it("rejects stale packet values against the active release config", () => {
    expect(
      submissionPacketMatchesReleaseConfig(
        packet({
          urls: {
            ...releaseConfig.urls,
            support_url: "https://stale.memoryhive.io/support",
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
    expect(
      submissionPacketMatchesReleaseConfig(
        packet({
          app_store: {
            ...packet().app_store,
            privacy_draft: {
              external_ai_processing: { mode: "none" },
              production_telemetry: { mode: "crash_reporting" },
            },
          },
        }),
        releaseConfig,
      ),
    ).toBe(false);
  });

  it("rejects committed reviewer passwords", () => {
    expect(
      submissionPacketKeepsReviewPasswordsOutOfSource(
        packet({
          app_store: {
            ...packet().app_store,
            review_account: {
              email: releaseConfig.reviewAccountEmail,
              password: "TemporaryPassword123!",
            },
          },
        }),
      ),
    ).toBe(false);
  });

  it("enforces platform copy length limits", () => {
    expect(
      appStoreSubtitleWithinLimit(
        packet({
          app_store: {
            ...packet().app_store,
            subtitle: "This subtitle is far too long for App Store metadata",
          },
        }),
      ),
    ).toBe(false);
    expect(
      googlePlayShortDescriptionWithinLimit(
        packet({
          google_play: {
            ...packet().google_play,
            short_description: "x".repeat(81),
          },
        }),
      ),
    ).toBe(false);
  });
});
