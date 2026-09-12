import { describe, expect, it } from "vitest";

import {
  fallbackApiUrl,
  isExternalAiDisclosureConsistent,
  isKnownPrivacyDisclosureValue,
  isProductionEmail,
  isProductionHttpsUrl,
  resolveStoreReleaseConfig,
} from "../scripts/store-release-config.mjs";

const emptyEnvFile = { values: {} };

function readTemplate(values) {
  return (_relativePath, name) => values[name];
}

describe("store release config", () => {
  it("resolves production values from the template and script fallbacks", () => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({
        EXPO_PUBLIC_SUPPORT_URL: "https://app.memoryhive.io/support",
        EXPO_PUBLIC_PRIVACY_POLICY_URL: "https://app.memoryhive.io/privacy",
        VITE_SUPPORT_EMAIL: "support@memoryhive.io",
        STORE_REVIEW_ACCOUNT_EMAIL: "reviewer@memoryhive.io",
      }),
      envFile: emptyEnvFile,
      env: {},
    });

    expect(config.values.EXPO_PUBLIC_API_URL).toBe(fallbackApiUrl);
    expect(config.urls.support_url).toBe("https://app.memoryhive.io/support");
    expect(config.urls.privacy_policy_url).toBe("https://app.memoryhive.io/privacy");
    expect(config.contacts.support_email).toBe("support@memoryhive.io");
    expect(config.reviewAccountEmail).toBe("reviewer@memoryhive.io");
  });

  it("lets release env-file values override production template values", () => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({
        EXPO_PUBLIC_API_URL: "https://template.memoryhive.io/api/v1",
        VITE_SUPPORT_EMAIL: "support@template.memoryhive.io",
      }),
      envFile: {
        values: {
          EXPO_PUBLIC_API_URL: "https://file.memoryhive.io/api/v1",
          VITE_SUPPORT_EMAIL: "support@file.memoryhive.io",
        },
      },
      env: {},
    });

    expect(config.urls.api_url).toBe("https://file.memoryhive.io/api/v1");
    expect(config.contacts.support_email).toBe("support@file.memoryhive.io");
  });

  it("lets shell environment values override release env-file values", () => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({
        EXPO_PUBLIC_API_URL: "https://template.memoryhive.io/api/v1",
      }),
      envFile: {
        values: {
          EXPO_PUBLIC_API_URL: "https://file.memoryhive.io/api/v1",
          STORE_REVIEW_ACCOUNT_EMAIL: "reviewer@file.memoryhive.io",
        },
      },
      env: {
        EXPO_PUBLIC_API_URL: "https://env.memoryhive.io/api/v1",
        STORE_REVIEW_ACCOUNT_EMAIL: "reviewer@env.memoryhive.io",
      },
    });

    expect(config.urls.api_url).toBe("https://env.memoryhive.io/api/v1");
    expect(config.reviewAccountEmail).toBe("reviewer@env.memoryhive.io");
  });

  it("derives support, privacy, and deletion URLs from the API origin when omitted", () => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({}),
      envFile: {
        values: {
          EXPO_PUBLIC_API_URL: "https://release.memoryhive.io/api/v1",
        },
      },
      env: {},
    });

    expect(config.values.EXPO_PUBLIC_SUPPORT_URL).toBeUndefined();
    expect(config.values.EXPO_PUBLIC_PRIVACY_POLICY_URL).toBeUndefined();
    expect(config.urls.support_url).toBe("https://release.memoryhive.io/support");
    expect(config.urls.privacy_policy_url).toBe("https://release.memoryhive.io/privacy");
    expect(config.urls.account_deletion_url).toBe("https://release.memoryhive.io/account/delete");
  });

  it("validates production URLs as public HTTPS routes with exact paths", () => {
    expect(isProductionHttpsUrl("https://api.memoryhive.io/api/v1", "/api/v1")).toBe(true);
    expect(isProductionHttpsUrl("http://api.memoryhive.io/api/v1", "/api/v1")).toBe(false);
    expect(isProductionHttpsUrl("https://localhost/api/v1", "/api/v1")).toBe(false);
    expect(isProductionHttpsUrl("https://192.168.1.10/api/v1", "/api/v1")).toBe(false);
    expect(isProductionHttpsUrl("https://memoryhive.example.com/api/v1", "/api/v1")).toBe(
      false,
    );
    expect(isProductionHttpsUrl("https://api.memoryhive.io/api", "/api/v1")).toBe(false);
  });

  it("validates production emails as non-placeholder public-domain addresses", () => {
    expect(isProductionEmail("support@memoryhive.io")).toBe(true);
    expect(isProductionEmail("support")).toBe(false);
    expect(isProductionEmail("support@memoryhive.example.com")).toBe(false);
    expect(isProductionEmail("support@memoryhive.local")).toBe(false);
    expect(isProductionEmail(undefined)).toBe(false);
  });

  it("resolves privacy disclosures without exposing enrichment endpoint values", () => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({}),
      envFile: {
        values: {
          STORE_EXTERNAL_AI_PROCESSING: "third_party",
          STORE_PRODUCTION_TELEMETRY: "crash_reporting",
          N8N_WEBHOOK_URL: "https://automation.memoryhive.io/webhook/store-review",
        },
      },
      env: {},
    });

    expect(config.privacyDisclosures.external_ai_processing).toMatchObject({
      mode: "third_party",
      content_sent_to_processor: true,
      configured_backend_enrichment: true,
    });
    expect(config.privacyDisclosures.external_ai_processing.notes).not.toContain(
      "automation.memoryhive.io",
    );
    expect(config.privacyDisclosures.production_telemetry).toMatchObject({
      mode: "crash_reporting",
      production_telemetry_enabled: true,
    });
  });

  it("validates disclosure modes and catches enrichment/disclosure mismatches", () => {
    expect(isKnownPrivacyDisclosureValue("STORE_EXTERNAL_AI_PROCESSING", "self_hosted")).toBe(
      true,
    );
    expect(isKnownPrivacyDisclosureValue("STORE_EXTERNAL_AI_PROCESSING", "vendor")).toBe(false);
    expect(isKnownPrivacyDisclosureValue("STORE_PRODUCTION_TELEMETRY", "analytics")).toBe(true);
    expect(isKnownPrivacyDisclosureValue("STORE_PRODUCTION_TELEMETRY", "sessions")).toBe(false);

    const mismatch = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({}),
      envFile: {
        values: {
          STORE_EXTERNAL_AI_PROCESSING: "none",
          OLLAMA_BASE_URL: "https://ollama.memoryhive.io",
        },
      },
      env: {},
    });

    expect(isExternalAiDisclosureConsistent(mismatch)).toBe(false);
  });

  it.each([
    { OPENROUTER_ENABLED: "true" },
    { HUGGINGFACE_ENABLED: "true" },
    { OPENAI_COMPATIBLE_ENABLED: "true" },
    { AI_EMBEDDINGS_ROUTE: "ollama:nomic-embed-text" },
  ])("detects every AI provider family for store disclosure checks", (providerValues) => {
    const config = resolveStoreReleaseConfig({
      readTemplateValue: readTemplate({}),
      envFile: {
        values: { STORE_EXTERNAL_AI_PROCESSING: "none", ...providerValues },
      },
      env: {},
    });

    expect(isExternalAiDisclosureConsistent(config)).toBe(false);
    expect(config.privacyDisclosures.external_ai_processing.notes).not.toContain("https://");
  });
});
