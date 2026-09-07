export interface ApiRuntime {
  platform: string;
  webHostname?: string;
  expoHostUri?: string;
}

function hostnameFromExpoUri(uri?: string) {
  if (!uri) return undefined;
  try {
    const normalized = uri.includes("://") ? uri : `http://${uri}`;
    return new URL(normalized).hostname;
  } catch {
    return undefined;
  }
}

export function resolveApiUrl(
  configuredUrl: string | undefined,
  runtime: ApiRuntime,
) {
  if (configuredUrl?.trim()) return configuredUrl.trim().replace(/\/$/, "");

  const host =
    runtime.webHostname ||
    hostnameFromExpoUri(runtime.expoHostUri) ||
    (runtime.platform === "android" ? "10.0.2.2" : "localhost");
  return `http://${host}:8000/api/v1`;
}
