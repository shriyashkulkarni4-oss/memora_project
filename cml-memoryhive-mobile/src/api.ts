import Constants from "expo-constants";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { Platform } from "react-native";

import { resolveApiUrl } from "./api-url";
import { ApiError, type SyncApi } from "./sync";
import {
  clearSession,
  currentAccessToken,
  currentRefreshToken,
  saveSession,
} from "./session";
import {
  filenameFromDisposition,
  resolvePrivacyPolicyUrl,
  resolveSupportUrl,
} from "./account-helpers";
import type { AISuggestionDecisionPayload, Category, ChangePage, Item, ManagedTag, Tokens, User } from "./types";

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
export const PRIVACY_POLICY_URL = resolvePrivacyPolicyUrl(
  process.env.EXPO_PUBLIC_PRIVACY_POLICY_URL ??
    (Constants.expoConfig?.extra?.privacyPolicyUrl as string | undefined),
  API_URL,
);
export const SUPPORT_URL = resolveSupportUrl(
  process.env.EXPO_PUBLIC_SUPPORT_URL ??
    (Constants.expoConfig?.extra?.supportUrl as string | undefined),
  API_URL,
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

function authHeader(): Record<string, string> {
  const token = currentAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchAccountExportBlob(retry = true) {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/account/export`, { headers: authHeader() });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError(`Cannot reach Memoryhive API at ${API_URL}. ${message}`, 0);
  }
  if (response.status === 401 && retry && (await currentRefreshToken())) {
    await refresh();
    return fetchAccountExportBlob(false);
  }
  if (!response.ok) throw await responseError(response);
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition")),
  };
}

async function downloadAccountExport(retry = true): Promise<{ filename: string; uri?: string }> {
  const directory = FileSystem.cacheDirectory ?? FileSystem.documentDirectory;
  if (!directory) throw new ApiError("File storage is unavailable on this device", 0);
  const fallbackName = `memoryhive-export-${new Date().toISOString().slice(0, 10)}.zip`;
  const download = await FileSystem.downloadAsync(
    `${API_URL}/account/export`,
    `${directory}${fallbackName}`,
    { headers: authHeader() },
  );
  if (download.status === 401 && retry && (await currentRefreshToken())) {
    await refresh();
    return downloadAccountExport(false);
  }
  if (download.status < 200 || download.status >= 300) {
    throw new ApiError(`Export failed (${download.status})`, download.status);
  }
  const filename = filenameFromDisposition(
    download.headers["content-disposition"] ?? download.headers["Content-Disposition"],
  );
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(download.uri, {
      dialogTitle: "Export Memoryhive data",
      mimeType: "application/zip",
      UTI: "public.zip-archive",
    });
    return { filename };
  }
  return { filename, uri: download.uri };
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
  changePassword: (payload: { current_password: string; new_password: string }) =>
    request<void>(
      "/auth/change-password",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  updateAIPrivacy: (external_processing_allowed: boolean) =>
    request<User>("/auth/ai-privacy", {
      method: "PATCH",
      body: JSON.stringify({ external_processing_allowed }),
    }),
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
    } catch {
      // Local cleanup is owned by the caller and must not depend on network state.
    } finally {
      await clearSession();
    }
  },
};

export const accountApi = {
  async exportData() {
    if (Platform.OS !== "web") return downloadAccountExport();
    const { blob, filename } = await fetchAccountExportBlob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    return { filename };
  },
  remove: (password: string) =>
    request<void>("/account", {
      method: "DELETE",
      body: JSON.stringify({ password, confirmation: "DELETE" }),
    }),
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
    if (payload.category_id) form.append("category_id", payload.category_id);
    if (payload.tags?.length) form.append("tags", payload.tags.join(","));
    return request<Item>("/items/screenshot", { method: "POST", body: form });
  },
  update: (id, payload) =>
    request<Item>(`/items/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: (id) => request<void>(`/items/${id}`, { method: "DELETE" }),
  get: (id) => request<Item>(`/items/${id}`),
  changes: (since, cursor) =>
    request<ChangePage>(`/items/changes${query({ since, cursor, limit: "200" })}`),
  decideSuggestions: (id: string, payload: AISuggestionDecisionPayload) =>
    request<void>(`/items/${id}/suggestions/decisions`, { method: "POST", body: JSON.stringify(payload) }),
};

export const categoriesApi = {
  list: () => request<Category[]>("/categories"),
  create: (payload: { name: string; color: string; icon?: string; description?: string | null }) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify(payload) }),
  remove: (id: string) => request<void>(`/categories/${id}`, { method: "DELETE" }),
};

export const tagsApi = {
  list: () => request<ManagedTag[]>("/tags"),
  create: (payload: { name: string; color?: string }) =>
    request<ManagedTag>("/tags", { method: "POST", body: JSON.stringify(payload) }),
  remove: (id: string) => request<void>(`/tags/${id}`, { method: "DELETE" }),
};

export async function assetUrl(assetId: string) {
  return `${API_URL}/assets/${assetId}/download`;
}

export function retryItemProcessing(itemId: string) {
  return request(`/items/${itemId}/processing/retry`, { method: "POST" });
}
