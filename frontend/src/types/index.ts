// ============ ENUMS ============

export enum LinkSource {
  TWITTER = 'twitter',
  LINKEDIN = 'linkedin',
  YOUTUBE = 'youtube',
  GITHUB = 'github',
  ARTICLE = 'article',
  NEWS = 'news',
  SCREENSHOT = 'screenshot',
  MANUAL = 'manual',
  OTHER = 'other'
}

export enum LinkStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  FAILED = 'failed'
}

// ============ INTERFACES ============

export interface Tag {
  id: string;
  name: string;
  color: string;
  usageCount: number;
}

export interface Category {
  id: string;
  name: string;
  color: string;
  icon: string;
  description?: string;
  linkCount: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface AISummary {
  summary: string;
  keyPoints: string[];
  topics: string[];
  suggestedCategories: string[];
  suggestedTags: string[];
  processedAt: Date;
}

export interface ScreenshotData {
  fileUrl: string;
  thumbnailUrl?: string;
  ocrText?: string;
  ocrProcessed: boolean;
  fileSize: number;
}

export interface Link {
  id: string;
  userId: string;
  url: string;
  title: string;
  description?: string;
  favicon?: string;
  source: LinkSource;
  status: LinkStatus;
  categoryId?: string;
  category?: Category;
  tags: Tag[];
  aiSummary?: AISummary;
  screenshot?: ScreenshotData;
  isFavorite: boolean;
  isArchived: boolean;
  readCount: number;
  lastVisitedAt?: Date;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface LinkStats {
  totalLinks: number;
  favoriteLinks: number;
  archivedLinks: number;
  pendingProcessing: number;
  categoryCounts: { categoryId: string; categoryName: string; count: number }[];
  sourceCounts: { source: LinkSource; count: number }[];
  recentLinks: Link[];
  topTags: Tag[];
}

// ============ DTOs ============

export interface CreateLinkDto {
  url?: string;
  title?: string;
  description?: string;
  source: LinkSource;
  categoryId?: string;
  tags?: string[];
  notes?: string;
  screenshot?: File;
}

export interface UpdateLinkDto {
  title?: string;
  description?: string;
  categoryId?: string;
  tags?: string[];
  notes?: string;
  isFavorite?: boolean;
  isArchived?: boolean;
}

export interface LinkFilter {
  search?: string;
  categoryId?: string;
  tags?: string[];
  source?: LinkSource;
  status?: LinkStatus;
  isFavorite?: boolean;
  isArchived?: boolean;
  dateFrom?: Date;
  dateTo?: Date;
}
