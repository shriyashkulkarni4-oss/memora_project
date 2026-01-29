/**
 * Memora API Client
 * Handles all HTTP requests to the backend API
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Token management
let accessToken: string | null = localStorage.getItem('accessToken');

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    localStorage.setItem('accessToken', token);
  } else {
    localStorage.removeItem('accessToken');
  }
};

export const getAccessToken = () => accessToken;

// Base fetch wrapper
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      setAccessToken(null);
      window.location.href = '/login';
    }
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// File upload wrapper
async function uploadFile(
  endpoint: string,
  file: File,
  additionalData?: Record<string, string>
): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);

  if (additionalData) {
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value);
    });
  }

  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

// ============ AUTH API ============

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    fetchApi<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  register: (data: RegisterRequest) =>
    fetchApi<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMe: () => fetchApi<User>('/api/auth/me'),
};

// ============ LINKS API ============

export interface LinkResponse {
  id: string;
  user_id: string;
  url: string | null;
  title: string;
  description: string | null;
  favicon: string | null;
  source: string;
  status: string;
  category_id: string | null;
  tags: { id: string; name: string; color: string }[];
  ai_summary: {
    summary: string;
    keyPoints: string[];
    topics: string[];
  } | null;
  screenshot_url: string | null;
  is_favorite: boolean;
  is_archived: boolean;
  read_count: number;
  last_visited_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateLinkRequest {
  url?: string;
  title: string;
  description?: string;
  source?: string;
  category_id?: string;
  tags?: string[];
  notes?: string;
}

export interface UpdateLinkRequest {
  title?: string;
  description?: string;
  category_id?: string;
  tags?: string[];
  notes?: string;
  is_favorite?: boolean;
  is_archived?: boolean;
}

export interface LinkFilters {
  search?: string;
  category_id?: string;
  source?: string;
  is_favorite?: boolean;
  is_archived?: boolean;
  skip?: number;
  limit?: number;
}

export interface LinkStats {
  total_links: number;
  favorite_links: number;
  archived_links: number;
  pending_processing: number;
}

export const linksApi = {
  getAll: (filters: LinkFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value));
      }
    });
    return fetchApi<LinkResponse[]>(`/api/links?${params}`);
  },

  getById: (id: string) => fetchApi<LinkResponse>(`/api/links/${id}`),

  getStats: () => fetchApi<LinkStats>('/api/links/stats'),

  create: (data: CreateLinkRequest) =>
    fetchApi<LinkResponse>('/api/links', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateLinkRequest) =>
    fetchApi<LinkResponse>(`/api/links/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/links/${id}`, { method: 'DELETE' }),

  toggleFavorite: (id: string) =>
    fetchApi<{ is_favorite: boolean }>(`/api/links/${id}/favorite`, {
      method: 'POST',
    }),

  toggleArchive: (id: string) =>
    fetchApi<{ is_archived: boolean }>(`/api/links/${id}/archive`, {
      method: 'POST',
    }),

  uploadScreenshot: (file: File, data: { title: string; description?: string; category_id?: string }) =>
    uploadFile('/api/links/screenshot', file, data as Record<string, string>),
};

// ============ CATEGORIES API ============

export interface CategoryResponse {
  id: string;
  name: string;
  color: string;
  icon: string;
  description: string | null;
  link_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCategoryRequest {
  name: string;
  color?: string;
  icon?: string;
  description?: string;
}

export interface UpdateCategoryRequest {
  name?: string;
  color?: string;
  icon?: string;
  description?: string;
}

export const categoriesApi = {
  getAll: () => fetchApi<CategoryResponse[]>('/api/categories'),

  getById: (id: string) => fetchApi<CategoryResponse>(`/api/categories/${id}`),

  create: (data: CreateCategoryRequest) =>
    fetchApi<CategoryResponse>('/api/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateCategoryRequest) =>
    fetchApi<CategoryResponse>(`/api/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/categories/${id}`, { method: 'DELETE' }),
};

// ============ TAGS API ============

export interface TagResponse {
  id: string;
  name: string;
  color: string;
  usage_count: number;
}

export interface CreateTagRequest {
  name: string;
  color?: string;
}

export const tagsApi = {
  getAll: () => fetchApi<TagResponse[]>('/api/tags'),

  create: (data: CreateTagRequest) =>
    fetchApi<TagResponse>('/api/tags', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/tags/${id}`, { method: 'DELETE' }),
};
