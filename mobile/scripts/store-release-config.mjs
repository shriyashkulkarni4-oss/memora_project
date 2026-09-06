import { envFileValue } from "./store-env.mjs";

export const productionEnvTemplatePath = ".env.production.example";
export const fallbackWebOrigin = "https://memoryhive.example.com";
export const fallbackApiUrl = `${fallbackWebOrigin}/api/v1`;

export const productionUrlSpecs = [
  {
    name: "EXPO_PUBLIC_API_URL",
    key: "api_url",
    title: "Production API URL",
    requiredPath: "/api/v1",
    detail: "Set EXPO_PUBLIC_API_URL to a real public HTTPS /api/v1 endpoint before release.",
  },
  {
    name: "EXPO_PUBLIC_PRIVACY_POLICY_URL",
    key: "privacy_policy_url",
    title: "Production privacy URL",
    requiredPath: "/privacy",
    detail: "Set EXPO_PUBLIC_PRIVACY_POLICY_URL to the deployed public HTTPS /privacy route before release.",
  },
  {
    name: "EXPO_PUBLIC_SUPPORT_URL",
    key: "support_url",
    title: "Production support URL",
    requiredPath: "/support",
    detail: "Set EXPO_PUBLIC_SUPPORT_URL to the deployed public HTTPS /support route before release.",
  },
];

export const privacyDisclosureSpecs = [
  {
    name: "STORE_EXTERNAL_AI_PROCESSING",
    title: "External AI privacy disclosure",
    allowedValues: ["none", "self_hosted", "third_party"],
    detail:
      "Set STORE_EXTERNAL_AI_PROCESSING to none, self_hosted, or third_party before copying store privacy answers.",
  },
  {
    name: "STORE_PRODUCTION_TELEMETRY",
    title: "Production telemetry privacy disclosure",
    allowedValues: [
      "none",
      "analytics",
      "crash_reporting",
      "analytics_and_crash_reporting",
      "other",
    ],
    detail:
      "Set STORE_PRODUCTION_TELEMETRY to none, analytics, crash_reporting, analytics_and_crash_reporting, or other before copying store privacy answers.",
  },
];

const exampleDomainPattern = /(^|[.@/])example\.(com|org|net)(\/|$)/i;
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const fallbackSupportEmail = "support@memoryhive.example.com";
const fallbackReviewAccountEmail = "reviewer@memoryhive.example.com";
const fallbackExternalAiProcessing = "none";
const fallbackProductionTelemetry = "none";

function nonBlankValue(value) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function templateValue(readTemplateValue, name) {
  if (!readTemplateValue) return undefined;
  return nonBlankValue(readTemplateValue(productionEnvTemplatePath, name));
}

function releaseValue({ readTemplateValue, envFile, env }, name, fallback) {
  return (
    nonBlankValue(env?.[name]) ??
    envFileValue(envFile ?? { values: {} }, name) ??
    templateValue(readTemplateValue, name) ??
    fallback
  );
}

export function isPlaceholderValue(value) {
  return !value || exampleDomainPattern.test(value);
}

function isNonPublicIpv4(hostname) {
  const parts = hostname.split(".").map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return false;
  }
  const [first, second] = parts;
  return (
    first === 0 ||
    first === 10 ||
    first === 127 ||
    (first === 100 && second >= 64 && second <= 127) ||
    (first === 169 && second === 254) ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 0 && (parts[2] === 0 || parts[2] === 2)) ||
    (first === 192 && second === 168) ||
    (first === 198 && (second === 18 || second === 19)) ||
    (first === 198 && second === 51 && parts[2] === 100) ||
    (first === 203 && second === 0 && parts[2] === 113) ||
    first >= 224
  );
}

export function isLocalOrReservedHostname(hostname) {
  const normalized = hostname.toLowerCase().replace(/\.$/, "");
  return (
    normalized === "localhost" ||
    normalized === "0.0.0.0" ||
    normalized === "::1" ||
    normalized === "[::1]" ||
    normalized.endsWith(".localhost") ||
    normalized.endsWith(".local") ||
    normalized.endsWith(".test") ||
    normalized.endsWith(".invalid") ||
    isNonPublicIpv4(normalized)
  );
}

function normalizedPathname(pathname) {
  return pathname.replace(/\/+$/, "") || "/";
}

export function isProductionHttpsUrl(value, requiredPath) {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      !isPlaceholderValue(value) &&
      !isLocalOrReservedHostname(url.hostname) &&
      normalizedPathname(url.pathname) === requiredPath
    );
  } catch {
    return false;
  }
}

export function isProductionEmail(value) {
  if (isPlaceholderValue(value) || !emailPattern.test(value ?? "")) return false;
  const domain = value.split("@").at(1)?.toLowerCase() ?? "";
  return !isLocalOrReservedHostname(domain);
}

export function publicOriginFromReleaseUrl(value) {
  try {
    return new URL(value).origin;
  } catch {
    return fallbackWebOrigin;
  }
}

export function isKnownPrivacyDisclosureValue(name, value) {
  const spec = privacyDisclosureSpecs.find((candidate) => candidate.name === name);
  return Boolean(spec && spec.allowedValues.includes(value));
}

function externalAiDisclosure(mode, values) {
  const configuredBackendEnrichment = Boolean(values.OLLAMA_BASE_URL || values.N8N_WEBHOOK_URL);
  const contentSentToProcessor = mode !== "none";
  let notes = "No external AI processor is declared for store privacy answers.";
  if (mode === "self_hosted") {
    notes = "Production enrichment is declared as operator-managed AI/automation infrastructure.";
  }
  if (mode === "third_party") {
    notes = "Production enrichment is declared as a third-party AI/automation processor.";
  }
  if (configuredBackendEnrichment && mode === "none") {
    notes = "Backend enrichment endpoints are configured; update STORE_EXTERNAL_AI_PROCESSING before submission.";
  }
  return {
    mode,
    content_sent_to_processor: contentSentToProcessor,
    configured_backend_enrichment: configuredBackendEnrichment,
    notes,
  };
}

function telemetryDisclosure(mode) {
  const usesTelemetry = mode !== "none";
  const notes =
    mode === "none"
      ? "No production analytics or crash-reporting tooling is declared in this release handoff."
      : "Production telemetry is declared; verify store privacy/data-safety forms against the deployed tooling.";
  return {
    mode,
    production_telemetry_enabled: usesTelemetry,
    notes,
  };
}

export function isExternalAiDisclosureConsistent(config) {
  const disclosure = config.privacyDisclosures.external_ai_processing;
  return !disclosure.configured_backend_enrichment || disclosure.mode !== "none";
}

// Keep store:submission and store:check aligned on release-value precedence.
export function resolveStoreReleaseConfig({
  readTemplateValue,
  envFile = { values: {} },
  env = process.env,
} = {}) {
  const context = { readTemplateValue, envFile, env };
  const values = {
    EXPO_PUBLIC_API_URL: releaseValue(context, "EXPO_PUBLIC_API_URL", fallbackApiUrl),
    EXPO_PUBLIC_PRIVACY_POLICY_URL: releaseValue(context, "EXPO_PUBLIC_PRIVACY_POLICY_URL"),
    EXPO_PUBLIC_SUPPORT_URL: releaseValue(context, "EXPO_PUBLIC_SUPPORT_URL"),
    VITE_SUPPORT_EMAIL: releaseValue(context, "VITE_SUPPORT_EMAIL", fallbackSupportEmail),
    STORE_REVIEW_ACCOUNT_EMAIL: releaseValue(
      context,
      "STORE_REVIEW_ACCOUNT_EMAIL",
      fallbackReviewAccountEmail,
    ),
    STORE_EXTERNAL_AI_PROCESSING: releaseValue(
      context,
      "STORE_EXTERNAL_AI_PROCESSING",
      fallbackExternalAiProcessing,
    ),
    STORE_PRODUCTION_TELEMETRY: releaseValue(
      context,
      "STORE_PRODUCTION_TELEMETRY",
      fallbackProductionTelemetry,
    ),
    OLLAMA_BASE_URL: releaseValue(context, "OLLAMA_BASE_URL"),
    N8N_WEBHOOK_URL: releaseValue(context, "N8N_WEBHOOK_URL"),
  };
  const webOrigin = publicOriginFromReleaseUrl(
    values.EXPO_PUBLIC_SUPPORT_URL ?? values.EXPO_PUBLIC_PRIVACY_POLICY_URL ?? values.EXPO_PUBLIC_API_URL,
  );

  return {
    values,
    urls: {
      api_url: values.EXPO_PUBLIC_API_URL,
      support_url: values.EXPO_PUBLIC_SUPPORT_URL ?? `${webOrigin}/support`,
      privacy_policy_url: values.EXPO_PUBLIC_PRIVACY_POLICY_URL ?? `${webOrigin}/privacy`,
      account_deletion_url: `${webOrigin}/account/delete`,
    },
    contacts: {
      support_email: values.VITE_SUPPORT_EMAIL,
    },
    reviewAccountEmail: values.STORE_REVIEW_ACCOUNT_EMAIL,
    privacyDisclosures: {
      external_ai_processing: externalAiDisclosure(values.STORE_EXTERNAL_AI_PROCESSING, values),
      production_telemetry: telemetryDisclosure(values.STORE_PRODUCTION_TELEMETRY),
    },
  };
}
