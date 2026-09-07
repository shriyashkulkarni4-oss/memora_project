function resolvePublicWebUrl(
  configuredUrl: string | undefined,
  apiUrl: string,
  path: "/privacy" | "/support",
) {
  if (configuredUrl?.trim()) return configuredUrl.trim();
  return new URL(path, apiUrl).toString();
}

export function resolvePrivacyPolicyUrl(configuredUrl: string | undefined, apiUrl: string) {
  return resolvePublicWebUrl(configuredUrl, apiUrl, "/privacy");
}

export function resolveSupportUrl(configuredUrl: string | undefined, apiUrl: string) {
  return resolvePublicWebUrl(configuredUrl, apiUrl, "/support");
}

export function filenameFromDisposition(disposition?: string | null) {
  return disposition?.match(/filename="?([^";]+)"?/)?.[1] ?? "memoryhive-export.zip";
}
