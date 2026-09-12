export type ItemType = "link" | "screenshot" | "text";
export type ProcessingStatus = "pending" | "processing" | "ready" | "failed" | "skipped";
export type AnalysisStatus = "not_analyzed" | "pending" | "scheduled" | "analyzing" | "analyzed" | "degraded" | "failed" | "skipped";

export interface TagReference {
  id: string;
  name: string;
  color: string;
}

export interface Category {
  id: string;
  name: string;
  color: string;
  icon: string;
  description: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
  search_match?: {
    score: number;
    reasons: string[];
    snippet: string | null;
    semantic_score: number | null;
  } | null;
}

export interface ManagedTag extends TagReference {
  usage_count: number;
}

export interface Asset {
  id: string;
  mime_type: string;
  size_bytes: number;
  original_filename: string | null;
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
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  analysis_version: number;
  analysis_requested_at: string | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  category_id: string | null;
  tags: TagReference[];
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

export interface ItemCreate {
  id: string;
  type: ItemType;
  url?: string;
  raw_text?: string;
  title?: string;
  notes?: string;
  category_id?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ItemUpdate {
  expected_revision?: number;
  url?: string | null;
  raw_text?: string | null;
  title?: string | null;
  notes?: string | null;
  category_id?: string | null;
  tags?: string[];
  is_favorite?: boolean;
  is_archived?: boolean;
}

export interface AISuggestionDecision {
  suggestion_type: "tag" | "classification";
  value: string;
  action: "accept" | "reject" | "never" | "undo";
}

export interface AISuggestionDecisionPayload {
  client_id: string;
  analysis_version: number;
  expected_revision: number;
  decisions: AISuggestionDecision[];
}

export type MutationOperation = "create" | "update" | "delete" | "screenshot" | "suggestion";

export interface PendingMutation {
  sequence: number;
  itemId: string;
  operation: MutationOperation;
  payload: ItemCreate | ItemUpdate | AISuggestionDecisionPayload;
  localUri?: string;
  attempts: number;
}

export interface ChangePage {
  items: Item[];
  next_cursor: string | null;
  has_more: boolean;
  server_time: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  role?: "admin" | "user";
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}
