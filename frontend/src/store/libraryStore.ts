import { create } from 'zustand';
import { fixtureCategories, fixtureItems, fixtureTags } from '../data/fixtures';
import type {
  Category,
  CreateItemRequest,
  Item,
  ItemType,
  ManagedTag,
  UpdateItemRequest,
} from '../types/api';

export type ViewMode = 'grid' | 'list';

interface LibraryState {
  items: Item[];
  categories: Category[];
  tags: ManagedTag[];
  query: string;
  typeFilter: ItemType | 'all';
  viewMode: ViewMode;
  captureOpen: boolean;
  setQuery: (query: string) => void;
  setTypeFilter: (type: ItemType | 'all') => void;
  setViewMode: (mode: ViewMode) => void;
  setCaptureOpen: (open: boolean) => void;
  createItem: (data: CreateItemRequest, previewUrl?: string) => Item;
  updateItem: (id: string, data: UpdateItemRequest) => void;
  toggleFavorite: (id: string) => void;
  toggleArchive: (id: string) => void;
  deleteItem: (id: string) => void;
  createCategory: (name: string, color: string) => void;
  deleteCategory: (id: string) => void;
  deleteTag: (id: string) => void;
}

const now = () => new Date().toISOString();

export const useLibraryStore = create<LibraryState>((set, get) => ({
  items: fixtureItems,
  categories: fixtureCategories,
  tags: fixtureTags,
  query: '',
  typeFilter: 'all',
  viewMode: 'grid',
  captureOpen: false,
  setQuery: (query) => set({ query }),
  setTypeFilter: (typeFilter) => set({ typeFilter }),
  setViewMode: (viewMode) => set({ viewMode }),
  setCaptureOpen: (captureOpen) => set({ captureOpen }),
  createItem: (data, previewUrl) => {
    const createdAt = data.created_at ?? now();
    const existingTags = get().tags;
    const itemTags = (data.tags ?? []).map((name) => {
      const normalized = name.trim().toLowerCase();
      const existing = existingTags.find((tag) => tag.name === normalized);
      if (existing) return existing;
      return {
        id: crypto.randomUUID(),
        name: normalized,
        color: '#64748b',
        usage_count: 1,
      };
    });
    const newTags = itemTags.filter(
      (tag) => !existingTags.some((existing) => existing.id === tag.id),
    );
    const url = data.url ?? null;
    const item: Item = {
      id: data.id ?? crypto.randomUUID(),
      user_id: '01a4dc43-39a8-4f09-b2f1-71a0a8b0fbde',
      type: data.type,
      url,
      raw_text: data.raw_text ?? null,
      title: data.title ?? null,
      description: data.description ?? null,
      notes: data.notes ?? null,
      source: data.source ?? (data.type === 'screenshot' ? 'screenshot' : 'manual'),
      source_domain: url ? new URL(url).hostname : null,
      author: null,
      published_at: null,
      favicon_url: null,
      extracted_text: null,
      language: data.type === 'text' ? 'en' : null,
      summary: null,
      metadata: previewUrl ? { ...data.metadata, preview_url: previewUrl } : (data.metadata ?? null),
      processing_status: data.type === 'text' ? 'ready' : 'pending',
      processing_error: null,
      category_id: data.category_id ?? null,
      tags: itemTags,
      assets: [],
      is_favorite: false,
      is_archived: false,
      read_count: 0,
      last_visited_at: null,
      revision: 1,
      deleted_at: null,
      created_at: createdAt,
      updated_at: createdAt,
    };
    set((state) => ({
      items: [item, ...state.items],
      tags: [...state.tags, ...newTags],
      captureOpen: false,
    }));
    return item;
  },
  updateItem: (id, data) => {
    const tagNames = data.tags;
    set((state) => ({
      items: state.items.map((item) => {
        if (item.id !== id) return item;
        const resolvedTags = tagNames?.map((name) => {
          const normalized = name.trim().toLowerCase();
          return (
            state.tags.find((tag) => tag.name === normalized) ?? {
              id: crypto.randomUUID(),
              name: normalized,
              color: '#64748b',
            }
          );
        });
        return {
          ...item,
          tags: resolvedTags ?? item.tags,
          url: data.url === undefined ? item.url : data.url,
          raw_text: data.raw_text === undefined ? item.raw_text : data.raw_text,
          title: data.title === undefined ? item.title : data.title,
          description:
            data.description === undefined ? item.description : data.description,
          notes: data.notes === undefined ? item.notes : data.notes,
          category_id:
            data.category_id === undefined ? item.category_id : data.category_id,
          source: data.source === undefined ? item.source : data.source,
          is_favorite:
            data.is_favorite === undefined ? item.is_favorite : data.is_favorite,
          is_archived:
            data.is_archived === undefined ? item.is_archived : data.is_archived,
          revision: item.revision + 1,
          updated_at: now(),
        };
      }),
    }));
  },
  toggleFavorite: (id) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id
          ? {
              ...item,
              is_favorite: !item.is_favorite,
              revision: item.revision + 1,
              updated_at: now(),
            }
          : item,
      ),
    })),
  toggleArchive: (id) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id
          ? {
              ...item,
              is_archived: !item.is_archived,
              revision: item.revision + 1,
              updated_at: now(),
            }
          : item,
      ),
    })),
  deleteItem: (id) => set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
  createCategory: (name, color) =>
    set((state) => ({
      categories: [
        ...state.categories,
        {
          id: crypto.randomUUID(),
          name: name.trim(),
          color,
          icon: 'folder',
          description: null,
          item_count: 0,
          created_at: now(),
          updated_at: now(),
        },
      ],
    })),
  deleteCategory: (id) =>
    set((state) => ({
      categories: state.categories.filter((category) => category.id !== id),
      items: state.items.map((item) =>
        item.category_id === id ? { ...item, category_id: null } : item,
      ),
    })),
  deleteTag: (id) =>
    set((state) => ({
      tags: state.tags.filter((tag) => tag.id !== id),
      items: state.items.map((item) => ({
        ...item,
        tags: item.tags.filter((tag) => tag.id !== id),
      })),
    })),
}));
