import Constants from "expo-constants";
import { Platform } from "react-native";

import { resolveApiUrl } from "./api-url";
import { ApiError, type SyncApi } from "./sync";
import {
  clearSession,
  currentAccessToken,
  currentRefreshToken,
  saveSession,
} from "./session";
import type { ChangePage, Item, Tokens, User } from "./types";

export const API_URL = resolveApiUrl(
  process.env.EXPO_PUBLIC_API_URL ??
    (Constants.expoConfig?.extra?.apiUrl as string | undefined),
  {
    platform: Platform.OS,
    webHostname:
      Platform.OS === "web" && typeof window !== "undefined"
        ? window.location.hostname
        : undefined,
    expoHostUri: Constants.expoConfig?.hostUri,
  },
);
let refreshPromise: Promise<void> | undefined;

async function responseError(response: Response) {
  const body = (await response.json().catch(() => null)) as
    | { detail?: string; error?: { message?: string } }
    | null;
  return new ApiError(
    body?.error?.message ?? body?.detail ?? `Request failed (${response.status})`,
    response.status,
  );
}

async function refresh() {
  refreshPromise ??= (async () => {
    const refreshToken = await currentRefreshToken();
    if (!refreshToken) throw new ApiError("Your session has expired", 401);
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      await clearSession();
      throw await responseError(response);
    }
    await saveSession((await response.json()) as Tokens);
  })().finally(() => {
    refreshPromise = undefined;
  });
  return refreshPromise;
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = currentAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError(`Cannot reach Memoryhive API at ${API_URL}. ${message}`, 0);
  }
  if (response.status === 401 && retry && (await currentRefreshToken())) {
    await refresh();
    return request(path, options, false);
  }
  if (!response.ok) throw await responseError(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

function query(params: Record<string, string | undefined>) {
  const values = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => value && values.set(key, value));
  return values.size ? `?${values.toString()}` : "";
}

export const authApi = {
  register: (payload: { email: string; password: string; name?: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(payload) }, false),
  async login(payload: { email: string; password: string }) {
    const tokens = await request<Tokens>(
      "/auth/login",
      { method: "POST", body: JSON.stringify(payload) },
      false,
    );
    await saveSession(tokens);
    return request<User>("/auth/me");
  },
  me: () => request<User>("/auth/me"),
  async logout() {
    const refreshToken = await currentRefreshToken();
    try {
      if (refreshToken) {
        await request<void>(
          "/auth/logout",
          { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
          false,
        );
      }
    } finally {
      await clearSession();
    }
  },
};

export const syncApi: SyncApi = {
  create: (payload) =>
    request<Item>("/items", { method: "POST", body: JSON.stringify(payload) }),
  async uploadScreenshot(payload, localUri) {
    const form = new FormData();
    form.append("file", {
      uri: localUri,
      name: `memoryhive-${payload.id}.jpg`,
      type: "image/jpeg",
    } as unknown as Blob);
    form.append("id", payload.id);
    if (payload.title) form.append("title", payload.title);
    if (payload.notes) form.append("notes", payload.notes);
    if (payload.tags?.length) form.append("tags", payload.tags.join(","));
    return request<Item>("/items/screenshot", { method: "POST", body: form });
  },
  update: (id, payload) =>
    request<Item>(`/items/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: (id) => request<void>(`/items/${id}`, { method: "DELETE" }),
  get: (id) => request<Item>(`/items/${id}`),
  changes: (since, cursor) =>
    request<ChangePage>(`/items/changes${query({ since, cursor, limit: "200" })}`),
};

export async function assetUrl(assetId: string) {
  return `${API_URL}/assets/${assetId}/download`;
}

export function retryItemProcessing(itemId: string) {
  return request(`/items/${itemId}/processing/retry`, { method: "POST" });
}
