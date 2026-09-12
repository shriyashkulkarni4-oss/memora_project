/** Canonical /api/v1 contracts. Keep field names aligned with OpenAPI. */

export type ItemType = 'link' | 'screenshot' | 'text';

export type ProcessingStatus =
  | 'pending'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'skipped';

export type AdminProcessingJobStatus =
  | 'pending'
  | 'scheduled'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'cancelled';

export type AnalysisStatus =
  | 'not_analyzed'
  | 'pending'
  | 'scheduled'
  | 'analyzing'
  | 'analyzed'
  | 'degraded'
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

export interface SearchMatch {
  score: number;
  reasons: Array<'exact' | 'phrase' | 'semantic' | 'tag' | 'source' | string>;
  snippet: string | null;
  semantic_score: number | null;
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
  search_match?: SearchMatch | null;
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

export interface MemoryMatch {
  item: Item;
  score: number;
  reasons: string[];
  semantic_score: number | null;
}

export interface DuplicateMatch extends MemoryMatch {
  duplicate_kind: 'exact_url' | 'exact_content' | 'near_semantic';
}

export interface ResurfacingPage {
  items: MemoryMatch[];
  generated_at: string;
}

export interface MemoryFeedback {
  id: string;
  item_id: string;
  action: string;
  reverses_id: string | null;
  created_at: string;
}

export interface GroundedRecall {
  answer: string;
  claims: { text: string; citation_ids: number[] }[];
  citations: { citation_id: number; item_id: string; title: string | null; passage: string }[];
  insufficient_evidence: boolean;
  provider: string | null;
  model: string | null;
  latency_ms: number | null;
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
}

export interface ManagedTag extends ItemTag {
  usage_count: number;
}

export interface ItemStats {
  total_items: number;
  active_items: number;
  favorite_items: number;
  archived_items: number;
  pending_processing: number;
  failed_processing: number;
  pending_analysis: number;
  failed_analysis: number;
  by_type: Record<ItemType, number>;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  role: 'admin' | 'user';
  is_active: boolean;
  ai_external_processing_allowed: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminDashboard {
  users_total: number;
  active_users: number;
  disabled_users: number;
  admin_users: number;
  items_total: number;
  archived_items: number;
  assets_total: number;
  storage_bytes: number;
  processing_pending: number;
  processing_failed: number;
  analysis_pending: number;
  analysis_failed: number;
}

export interface AdminUser extends User {
  item_count: number;
  asset_count: number;
  storage_bytes: number;
}

export interface AdminUsersPage {
  users: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminProcessingJob {
  id: string;
  item_id: string;
  item_title: string | null;
  item_type: ItemType;
  item_processing_status: ProcessingStatus;
  analysis_version: number | null;
  execution_backend: 'database' | 'temporal';
  reason: string;
  temporal_workflow_id: string | null;
  stage: string;
  content_hash: string | null;
  correlation_id: string;
  ai_provider: string | null;
  ai_model: string | null;
  cancel_requested: boolean;
  user_id: string;
  user_email: string;
  status: AdminProcessingJobStatus;
  attempts: number;
  max_attempts: number;
  next_attempt_at: string;
  locked_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AdminAnalysisProviderMetric {
  provider: string;
  runs: number;
  successes: number;
  failures: number;
  average_latency_ms: number | null;
}

export interface AdminAnalysisRecentError {
  item_reference: string;
  job_id: string | null;
  workflow_id: string | null;
  correlation_id: string | null;
  stage: string;
  provider: string | null;
  code: string;
  occurred_at: string;
}

export interface AdminAnalysisRunSummary {
  item_id: string;
  item_reference: string;
  job_id: string;
  workflow_id: string | null;
  correlation_id: string;
  analysis_version: number | null;
  backend: 'database' | 'temporal';
  stage: string;
  provider: string | null;
  model_alias: string | null;
  status: AdminProcessingJobStatus;
  analysis_status: AnalysisStatus;
  enrichment_mode: 'ai' | 'deterministic' | 'no_enrichment';
  attempts: number;
  max_attempts: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error_code: string | null;
}

export interface AdminAnalysisOperations {
  queue_depth: number;
  oldest_pending_age_seconds: number | null;
  status_counts: Record<string, number>;
  stage_counts: Record<string, number>;
  throughput_24h: number;
  success_rate_24h: number;
  degraded_rate_24h: number;
  temporal_enabled: boolean;
  temporal_ui_url: string | null;
  providers: AdminAnalysisProviderMetric[];
  recent_errors: AdminAnalysisRecentError[];
  recent_runs: AdminAnalysisRunSummary[];
}

export interface AdminAIProviderHealth {
  provider: string;
  available: boolean;
  latency_ms: number | null;
  message: string | null;
  capabilities: string[];
}

export interface AISuggestion {
  suggestion_type: 'tag' | 'classification';
  value: string;
  confidence: number | null;
  status: 'pending' | 'accepted' | 'rejected' | 'never';
  can_undo: boolean;
}

export interface AISuggestionOverview {
  item_id: string;
  analysis_version: number;
  item_revision: number;
  topics: string[];
  classification: string | null;
  suggestions: AISuggestion[];
}

export interface AISuggestionDecision {
  suggestion_type: 'tag' | 'classification';
  value: string;
  action: 'accept' | 'reject' | 'never' | 'undo';
}

export interface AdminProcessingJobsPage {
  jobs: AdminProcessingJob[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminBackupRecord {
  path: string;
  created_at: string;
  size_bytes: number;
  has_postgres_dump: boolean;
  has_minio_dir: boolean;
  has_checksums: boolean;
}

export interface AdminBackupStatus {
  configured: boolean;
  command: string | null;
  backup_root: string;
  retention_days: number;
  latest: AdminBackupRecord | null;
  recent: AdminBackupRecord[];
}

export interface AdminBackupRunResult {
  status: 'succeeded';
  exit_code: number;
  stdout: string;
  stderr: string;
  latest: AdminBackupRecord | null;
  duration_seconds: number;
}
