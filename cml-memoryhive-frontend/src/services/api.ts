import type {
  AdminAIProviderHealth, AdminAnalysisOperations, AdminBackupRunResult, AdminBackupStatus, AdminDashboard, AdminProcessingJob, AdminProcessingJobsPage, AdminUser, AdminUsersPage, AISuggestionDecision, AISuggestionOverview, Category, CreateItemRequest,
  DuplicateMatch, GroundedRecall, Item, ItemPage, ItemStats, ItemType, ManagedTag, MemoryFeedback, MemoryMatch, ProcessingStatus, ResurfacingPage, UpdateItemRequest, User,
} from '../types/api';

const API_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');
const ACCESS_KEY = 'memoryhive.accessToken';
const REFRESH_KEY = 'memoryhive.refreshToken';
let accessToken = localStorage.getItem(ACCESS_KEY);
let refreshPromise: Promise<void> | null = null;

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export class ApiClientError extends Error {
  constructor(message: string, public readonly status: number, public readonly code = 'request_failed') {
    super(message);
  }
}

function saveTokens(tokens: TokenPair | null) {
  accessToken = tokens?.access_token ?? null;
  if (tokens) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } else {
    Object.keys(localStorage)
      .filter((key) => key.startsWith('memoryhive.'))
      .forEach((key) => localStorage.removeItem(key));
  }
}

export const hasSession = () => Boolean(accessToken || localStorage.getItem(REFRESH_KEY));

async function parseError(response: Response): Promise<ApiClientError> {
  const body = await response.json().catch(() => null) as {
    detail?: string;
    error?: { code?: string; message?: string };
  } | null;
  return new ApiClientError(
    body?.error?.message || body?.detail || `Request failed (${response.status})`,
    response.status,
    body?.error?.code,
  );
}

async function refreshSession() {
  if (refreshPromise) return refreshPromise;
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) throw new ApiClientError('Your session has expired', 401, 'session_expired');
  refreshPromise = (async () => {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      saveTokens(null);
      window.dispatchEvent(new CustomEvent('memoryhive:session-expired', {
        detail: { message: 'Your session expired. Sign in again.' },
      }));
      throw await parseError(response);
    }
    saveTokens(await response.json() as TokenPair);
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}

async function request<T>(endpoint: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
  if (response.status === 401 && retry && localStorage.getItem(REFRESH_KEY)) {
    await refreshSession();
    return request<T>(endpoint, options, false);
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestBlob(endpoint: string, retry = true) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (response.status === 401 && retry && localStorage.getItem(REFRESH_KEY)) {
    await refreshSession();
    return requestBlob(endpoint, false);
  }
  if (!response.ok) throw await parseError(response);
  return {
    blob: await response.blob(),
    disposition: response.headers.get('Content-Disposition'),
  };
}

export const authApi = {
  register: (data: { email: string; password: string; name?: string }) =>
    request<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }, false),
  login: async (data: { email: string; password: string }) => {
    const tokens = await request<TokenPair>('/auth/login', { method: 'POST', body: JSON.stringify(data) }, false);
    saveTokens(tokens);
    return tokens;
  },
  restore: async () => {
    if (!accessToken) await refreshSession();
    try { return await request<User>('/auth/me'); }
    catch (error) { saveTokens(null); throw error; }
  },
  me: () => request<User>('/auth/me'),
  changePassword: (data: { current_password: string; new_password: string }) =>
    request<void>('/auth/change-password', { method: 'POST', body: JSON.stringify(data) }),
  updateAIPrivacy: (external_processing_allowed: boolean) =>
    request<User>('/auth/ai-privacy', { method: 'PATCH', body: JSON.stringify({ external_processing_allowed }) }),
  clearSession: () => saveTokens(null),
  logout: async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    try {
      if (refreshToken) await request<void>('/auth/logout', {
        method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }),
      }, false);
    } finally { saveTokens(null); }
  },
};

export interface ItemFilters {
  q?: string;
  cursor?: string;
  limit?: number;
  type?: ItemType;
  source?: string;
  category_id?: string;
  is_favorite?: boolean;
  is_archived?: boolean;
  processing_status?: ProcessingStatus;
  tag?: string[];
}

function queryString(filters: Record<string, unknown>) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) value.forEach((entry) => params.append(key, String(entry)));
    else params.set(key, String(value));
  });
  return params.size ? `?${params}` : '';
}

function upload<T>(endpoint: string, form: FormData, onProgress?: (percent: number) => void, retry = true): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}${endpoint}`);
    if (accessToken) xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new ApiClientError('Upload failed', 0));
    xhr.onload = async () => {
      if (xhr.status === 401 && retry && localStorage.getItem(REFRESH_KEY)) {
        try { await refreshSession(); resolve(await upload<T>(endpoint, form, onProgress, false)); }
        catch (error) { reject(error); }
        return;
      }
      type UploadBody = T & { detail?: string; error?: { message?: string; code?: string } };
      let body: UploadBody | null;
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) as UploadBody : null;
      } catch {
        reject(new ApiClientError('Upload returned an invalid response', xhr.status));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300 && body) resolve(body);
      else reject(new ApiClientError(body?.error?.message || body?.detail || 'Upload failed', xhr.status, body?.error?.code));
    };
    xhr.send(form);
  });
}

export const itemsApi = {
  list: (filters: ItemFilters = {}) => request<ItemPage>(`/items${queryString(filters as Record<string, unknown>)}`),
  get: (id: string) => request<Item>(`/items/${id}`),
  stats: () => request<ItemStats>('/items/stats'),
  create: (data: CreateItemRequest) => request<Item>('/items', { method: 'POST', body: JSON.stringify(data) }),
  createScreenshot: (data: CreateItemRequest, file: File, onProgress?: (percent: number) => void) => {
    const form = new FormData();
    form.set('file', file);
    if (data.id) form.set('id', data.id);
    if (data.title) form.set('title', data.title);
    if (data.description) form.set('description', data.description);
    if (data.notes) form.set('notes', data.notes);
    if (data.source) form.set('source', data.source);
    if (data.category_id) form.set('category_id', data.category_id);
    if (data.tags?.length) form.set('tags', data.tags.join(','));
    return upload<Item>('/items/screenshot', form, onProgress);
  },
  createDocument: (data: CreateItemRequest, file: File, onProgress?: (percent: number) => void) => {
    const form = new FormData();
    form.set('file', file);
    if (data.id) form.set('id', data.id);
    if (data.title) form.set('title', data.title);
    if (data.description) form.set('description', data.description);
    if (data.notes) form.set('notes', data.notes);
    if (data.source) form.set('source', data.source);
    if (data.category_id) form.set('category_id', data.category_id);
    if (data.tags?.length) form.set('tags', data.tags.join(','));
    return upload<Item>('/items/document', form, onProgress);
  },
  update: (id: string, data: UpdateItemRequest) => request<Item>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  retryProcessing: (id: string) => request(`/items/${id}/processing/retry`, { method: 'POST' }),
  related: (id: string) => request<MemoryMatch[]>(`/items/${id}/related`),
  duplicates: (id: string) => request<DuplicateMatch[]>(`/items/${id}/duplicates`),
  resurfacing: () => request<ResurfacingPage>('/items/resurfacing'),
  recall: (question: string) => request<GroundedRecall>('/items/recall', { method: 'POST', body: JSON.stringify({ question }) }),
  resurfacingFeedback: (id: string, data: { action: 'dismiss' | 'pin' | 'useful' | 'undo'; client_id: string; reverses_id?: string }) =>
    request<MemoryFeedback>(`/items/resurfacing/${id}/feedback`, { method: 'POST', body: JSON.stringify(data) }),
  suggestions: (id: string) => request<AISuggestionOverview>(`/items/${id}/suggestions`),
  decideSuggestions: (id: string, data: { client_id: string; analysis_version: number; expected_revision: number; decisions: AISuggestionDecision[] }) =>
    request<AISuggestionOverview>(`/items/${id}/suggestions/decisions`, { method: 'POST', body: JSON.stringify(data) }),
  remove: (id: string) => request<void>(`/items/${id}`, { method: 'DELETE' }),
  favorite: (id: string, value: boolean) => request<Item>(`/items/${id}/favorite`, { method: value ? 'PUT' : 'DELETE' }),
  archive: (id: string, value: boolean) => request<Item>(`/items/${id}/archive`, { method: value ? 'PUT' : 'DELETE' }),
  assetBlob: async (assetId: string) => {
    const response = await fetch(`${API_URL}/assets/${assetId}/download`, {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
    if (!response.ok) throw await parseError(response);
    return response.blob();
  },
};

export const categoriesApi = {
  list: () => request<Category[]>('/categories'),
  create: (data: { name: string; color: string; icon?: string }) => request<Category>('/categories', { method: 'POST', body: JSON.stringify(data) }),
  remove: (id: string) => request<void>(`/categories/${id}`, { method: 'DELETE' }),
};

export const tagsApi = {
  list: () => request<ManagedTag[]>('/tags'),
  create: (data: { name: string; color?: string }) => request<ManagedTag>('/tags', { method: 'POST', body: JSON.stringify(data) }),
  remove: (id: string) => request<void>(`/tags/${id}`, { method: 'DELETE' }),
};

export const accountApi = {
  export: () => requestBlob('/account/export'),
  remove: (password: string) => request<void>('/account', {
    method: 'DELETE',
    body: JSON.stringify({ password, confirmation: 'DELETE' }),
  }),
};

export const adminApi = {
  dashboard: () => request<AdminDashboard>('/admin/dashboard'),
  backupStatus: () => request<AdminBackupStatus>('/admin/backup'),
  runBackup: () => request<AdminBackupRunResult>('/admin/backup/run', { method: 'POST' }),
  processingJobs: (filters: { status?: 'pending' | 'processing' | 'completed' | 'failed'; limit?: number; offset?: number } = {}) =>
    request<AdminProcessingJobsPage>(`/admin/processing/jobs${queryString(filters)}`),
  retryProcessingJob: (id: string) =>
    request<AdminProcessingJob>(`/admin/processing/jobs/${id}/retry`, { method: 'POST', body: JSON.stringify({ confirmation: 'RETRY' }) }),
  cancelProcessingJob: (id: string) =>
    request<AdminProcessingJob>(`/admin/processing/jobs/${id}/cancel`, { method: 'POST', body: JSON.stringify({ confirmation: 'CANCEL' }) }),
  reanalyzeItem: (id: string) =>
    request<AdminProcessingJob>(`/admin/items/${id}/reanalyze`, { method: 'POST', body: JSON.stringify({ confirmation: 'REANALYZE' }) }),
  analysisOperations: () => request<AdminAnalysisOperations>('/admin/analysis/operations'),
  providerHealth: () => request<AdminAIProviderHealth[]>('/admin/ai/providers/health'),
  users: (filters: { limit?: number; offset?: number } = {}) =>
    request<AdminUsersPage>(`/admin/users${queryString(filters)}`),
  updateUser: (id: string, data: { role?: AdminUser['role']; is_active?: boolean }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  removeUser: (id: string) => request<void>(`/admin/users/${id}`, { method: 'DELETE' }),
};
