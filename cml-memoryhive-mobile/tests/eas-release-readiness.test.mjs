import { describe, expect, it } from "vitest";

import {
  easAndroidCredentialsEvidenceReady,
  easBuildProfilesReady,
  easCiBuildPreflightErrors,
  easCliConfigReady,
  easIosCredentialsEvidenceReady,
  easProductionEnvironmentEvidenceReady,
  easProjectIdentityReady,
  easReleaseEvidenceReady,
  easSubmitProfileReady,
} from "../scripts/eas-release-readiness.mjs";

const projectId = "123e4567-e89b-12d3-a456-426614174000";

const appConfig = {
  extra: {
    eas: {
      projectId,
    },
  },
};

const releaseConfig = {
  urls: {
    api_url: "https://app.memoryhive.io/api/v1",
    privacy_policy_url: "https://app.memoryhive.io/privacy",
    support_url: "https://app.memoryhive.io/support",
  },
};

function easConfig(overrides = {}) {
  return {
    cli: { version: ">= 16.0.0", appVersionSource: "remote" },
    build: {
      development: {
        developmentClient: true,
        distribution: "internal",
        environment: "development",
      },
      preview: {
        distribution: "internal",
        channel: "preview",
        environment: "preview",
      },
      production: {
        autoIncrement: true,
        channel: "production",
        environment: "production",
      },
    },
    submit: { production: {} },
    ...overrides,
  };
}

function evidence(overrides = {}) {
  const base = {
    eas: {
      project_id: projectId,
      production_environment: "production",
      production_environment_variables: [
        "EXPO_PUBLIC_API_URL",
        "EXPO_PUBLIC_PRIVACY_POLICY_URL",
        "EXPO_PUBLIC_SUPPORT_URL",
      ],
    },
    ios: {
      credentials_configured: true,
      bundle_identifier: "com.codingmonkeylabs.memoryhive",
      apple_team_id: "ABCDE12345",
      production_profile_verified: true,
      submit_profile_configured: true,
    },
    android: {
      credentials_configured: true,
      package_name: "com.codingmonkeylabs.memoryhive",
      keystore_configured: true,
      play_app_signing_enabled: true,
      service_account_configured: true,
      submit_profile_configured: true,
    },
  };
  return { ...base, ...overrides };
}

describe("EAS release readiness", () => {
  it("validates EAS project identity and local EAS config shape", () => {
    expect(easProjectIdentityReady(appConfig)).toBe(true);
    expect(easProjectIdentityReady({ extra: { eas: { projectId: "replace-me" } } })).toBe(
      false,
    );

    expect(easCliConfigReady(easConfig())).toBe(true);
    expect(easCliConfigReady(easConfig({ cli: { version: ">= 15.0.0" } }))).toBe(false);
    expect(easBuildProfilesReady(easConfig())).toBe(true);
    expect(easBuildProfilesReady(easConfig({ build: { production: {} } }))).toBe(false);
    expect(easSubmitProfileReady(easConfig())).toBe(true);
    expect(easSubmitProfileReady(easConfig({ submit: {} }))).toBe(false);
  });

  it("requires production EAS environment evidence matching the app project", () => {
    expect(
      easProductionEnvironmentEvidenceReady(evidence(), releaseConfig, appConfig),
    ).toBe(true);
    expect(
      easProductionEnvironmentEvidenceReady(
        evidence({
          eas: {
            ...evidence().eas,
            project_id: "00000000-0000-4000-8000-000000000000",
          },
        }),
        releaseConfig,
        appConfig,
      ),
    ).toBe(false);
    expect(
      easProductionEnvironmentEvidenceReady(
        evidence({
          eas: {
            ...evidence().eas,
            production_environment_variables: ["EXPO_PUBLIC_API_URL"],
          },
        }),
        releaseConfig,
        appConfig,
      ),
    ).toBe(false);
  });

  it("requires complete iOS and Android signing evidence", () => {
    expect(easIosCredentialsEvidenceReady(evidence())).toBe(true);
    expect(
      easIosCredentialsEvidenceReady({
        ios: { ...evidence().ios, apple_team_id: "replace-with-apple-team-id" },
      }),
    ).toBe(false);
    expect(easAndroidCredentialsEvidenceReady(evidence())).toBe(true);
    expect(
      easAndroidCredentialsEvidenceReady({
        android: { ...evidence().android, service_account_configured: false },
      }),
    ).toBe(false);
  });

  it("combines environment and signing evidence for final release readiness", () => {
    expect(easReleaseEvidenceReady(evidence(), releaseConfig, appConfig)).toBe(true);
    expect(
      easReleaseEvidenceReady(
        evidence({ android: { ...evidence().android, keystore_configured: false } }),
        releaseConfig,
        appConfig,
      ),
    ).toBe(false);
  });

  it("reports every non-interactive CI build prerequisite", () => {
    expect(
      easCiBuildPreflightErrors({
        appConfig,
        easConfig: easConfig(),
        expoToken: "expo-token",
      }),
    ).toEqual([]);

    expect(
      easCiBuildPreflightErrors({
        appConfig: { extra: { eas: {} } },
        easConfig: easConfig({
          cli: { version: ">= 15.0.0" },
          build: { production: {} },
        }),
        expoToken: "",
      }),
    ).toHaveLength(4);
  });
});
