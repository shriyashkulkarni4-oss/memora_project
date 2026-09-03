/** Canonical /api/v1 contracts. Keep field names aligned with OpenAPI. */

export type ItemType = 'link' | 'screenshot' | 'text';

export type ProcessingStatus =
  | 'pending'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'skipped';

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | unknown[] | null;
  };
}

export interface ItemTag {
  id: string;
  name: string;
  color: string;
}

export interface Asset {
  id: string;
  mime_type: string;
  size_bytes: number;
  original_filename: string | null;
  sha256: string | null;
  width: number | null;
  height: number | null;
  created_at: string;
}

export interface Item {
  id: string;
  user_id: string;
  type: ItemType;
  url: string | null;
  raw_text: string | null;
  title: string | null;
  description: string | null;
  notes: string | null;
  source: string | null;
  source_domain: string | null;
  author: string | null;
  published_at: string | null;
  favicon_url: string | null;
  extracted_text: string | null;
  language: string | null;
  summary: string | null;
  metadata: Record<string, unknown> | null;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  category_id: string | null;
  tags: ItemTag[];
  assets: Asset[];
  is_favorite: boolean;
  is_archived: boolean;
  read_count: number;
  last_visited_at: string | null;
  revision: number;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateItemRequest {
  id?: string;
  type: ItemType;
  url?: string;
  raw_text?: string;
  title?: string;
  description?: string;
  notes?: string;
  source?: string;
  category_id?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface UpdateItemRequest {
  expected_revision?: number;
  url?: string | null;
  raw_text?: string | null;
  title?: string | null;
  description?: string | null;
  notes?: string | null;
  source?: string | null;
  category_id?: string | null;
  tags?: string[];
  is_favorite?: boolean;
  is_archived?: boolean;
}

export interface ItemPage {
  items: Item[];
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
}
