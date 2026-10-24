import { create } from 'zustand';
import { categoriesApi, itemsApi, tagsApi } from '../services/api';
import { fixtureCategories, fixtureItems, fixtureTags } from '../data/fixtures';
import type { Category, CreateItemRequest, Item, ItemType, ManagedTag, UpdateItemRequest } from '../types/api';

export type ViewMode = 'grid' | 'list';
const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';
const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong';

interface LibraryState {
  items: Item[];
  searchResults: Item[] | null;
  categories: Category[];
  tags: ManagedTag[];
  query: string;
  typeFilter: ItemType | 'all';
  viewMode: ViewMode;
  captureOpen: boolean;
  isLoading: boolean;
  initialized: boolean;
  error: string | null;
  notice: string | null;
  uploadProgress: number | null;
  initialize: (force?: boolean) => Promise<void>;
  clear: () => void;
  dismissMessage: () => void;
  setQuery: (query: string) => void;
  search: (query: string) => Promise<void>;
  setTypeFilter: (type: ItemType | 'all') => void;
  setViewMode: (mode: ViewMode) => void;
  setCaptureOpen: (open: boolean) => void;
  createItem: (data: CreateItemRequest, file?: File) => Promise<Item>;
  updateItem: (id: string, data: UpdateItemRequest) => Promise<Item>;
  toggleFavorite: (id: string) => Promise<void>;
  toggleArchive: (id: string) => Promise<void>;
  deleteItem: (id: string) => Promise<void>;
  retryProcessing: (id: string) => Promise<void>;
  createCategory: (name: string, color: string) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;
  deleteTag: (id: string) => Promise<void>;
}

async function withPreviews(items: Item[]) {
  if (demoMode) return items;
  return Promise.all(items.map(async (item) => {
    const asset = item.assets[0];
    if (!asset) return item;
    try {
      const blob = await itemsApi.assetBlob(asset.id);
      return { ...item, metadata: { ...item.metadata, preview_url: URL.createObjectURL(blob) } };
    } catch {
      return item;
    }
  }));
}

function keepPreview(updated: Item, current: Item) {
  const preview = current.metadata?.preview_url;
  return preview ? { ...updated, metadata: { ...updated.metadata, preview_url: preview } } : updated;
}

function demoItem(data: CreateItemRequest, file?: File): Item {
  const createdAt = data.created_at ?? new Date().toISOString();
  const tags = (data.tags ?? []).map((name) => ({ id: crypto.randomUUID(), name: name.trim().toLowerCase(), color: '#64748b' }));
  return {
    id: data.id ?? crypto.randomUUID(), user_id: 'demo-user', type: data.type,
    url: data.url ?? null, raw_text: data.raw_text ?? null, title: data.title ?? null,
    description: data.description ?? null, notes: data.notes ?? null,
    source: data.source ?? (data.type === 'screenshot' ? 'screenshot' : 'manual'),
    source_domain: data.url ? new URL(data.url).hostname : null, author: null,
    published_at: null, favicon_url: null, extracted_text: null,
    language: data.type === 'text' ? 'en' : null, summary: null,
    metadata: file ? { ...data.metadata, preview_url: URL.createObjectURL(file) } : (data.metadata ?? null),
    processing_status: data.type === 'text' ? 'ready' : 'pending', processing_error: null,
    analysis_status: 'pending', analysis_error: null, analysis_version: 1,
    analysis_requested_at: createdAt, analysis_started_at: null, analysis_completed_at: null,
    category_id: data.category_id ?? null, tags, assets: [], is_favorite: false,
    is_archived: false, read_count: 0, last_visited_at: null, revision: 1,
    deleted_at: null, created_at: createdAt, updated_at: createdAt,
  };
}

export const useLibraryStore = create<LibraryState>((set, get) => ({
  items: demoMode ? fixtureItems : [],
  searchResults: null,
  categories: demoMode ? fixtureCategories : [],
  tags: demoMode ? fixtureTags : [],
  query: '', typeFilter: 'all', viewMode: 'grid', captureOpen: false,
  isLoading: false, initialized: demoMode, error: null, notice: null, uploadProgress: null,
  initialize: async (force = false) => {
    if (demoMode || (get().initialized && !force)) return;
    set({ isLoading: true, error: null });
    try {
      const [active, archived, categories, tags] = await Promise.all([
        itemsApi.list({ limit: 100 }), itemsApi.list({ limit: 100, is_archived: true }),
        categoriesApi.list(), tagsApi.list(),
      ]);
      set({
        items: await withPreviews([...active.items, ...archived.items]),
        categories, tags, initialized: true, isLoading: false,
      });
    } catch (error) {
      set({ error: message(error), isLoading: false });
    }
  },
  clear: () => set({ items: [], searchResults: null, categories: [], tags: [], initialized: false, error: null, notice: null }),
  dismissMessage: () => set({ error: null, notice: null }),
  setQuery: (query) => set({ query }),
  search: async (query) => {
    const value = query.trim();
    if (demoMode || !value) {
      set({ searchResults: null });
      return;
    }
    try {
      const [active, archived] = await Promise.all([
        itemsApi.list({ q: value, limit: 100 }),
        itemsApi.list({ q: value, limit: 100, is_archived: true }),
      ]);
      if (get().query.trim() === value) {
        set({ searchResults: await withPreviews([...active.items, ...archived.items]), error: null });
      }
    } catch (error) {
      if (get().query.trim() === value) set({ error: message(error) });
    }
  },
  setTypeFilter: (typeFilter) => set({ typeFilter }),
  setViewMode: (viewMode) => set({ viewMode }),
  setCaptureOpen: (captureOpen) => set({ captureOpen }),
  createItem: async (data, file) => {
    try {
      if (file) set({ uploadProgress: 0 });
      let item = demoMode ? demoItem(data, file) : data.type === 'screenshot' && file
        ? await itemsApi.createScreenshot(data, file, (uploadProgress) => set({ uploadProgress }))
        : data.type === 'document' && file
        ? await itemsApi.createDocument(data, file, (uploadProgress) => set({ uploadProgress }))
        : await itemsApi.create(data);
      [item] = await withPreviews([item]);
      set((state) => ({ items: [item, ...state.items], captureOpen: false, notice: 'Item saved', error: null, uploadProgress: null }));
      if (!demoMode) {
        const [tags, categories] = await Promise.all([tagsApi.list(), categoriesApi.list()]);
        set({ tags, categories });
      }
      return item;
    } catch (error) {
      set({ error: message(error), uploadProgress: null });
      throw error;
    }
  },
  updateItem: async (id, data) => {
    try {
      const current = get().items.find((item) => item.id === id);
      if (!current) throw new Error('Item not found');
      let updated = demoMode ? {
        ...current, ...data, revision: current.revision + 1, updated_at: new Date().toISOString(),
        tags: data.tags ? data.tags.map((name) => ({ id: crypto.randomUUID(), name, color: '#64748b' })) : current.tags,
      } as Item : await itemsApi.update(id, data);
      updated = keepPreview(updated, current);
      set((state) => ({ items: state.items.map((item) => item.id === id ? updated : item), notice: 'Changes saved', error: null }));
      return updated;
    } catch (error) {
      set({ error: message(error) });
      throw error;
    }
  },
  toggleFavorite: async (id) => {
    const before = get().items;
    const current = before.find((item) => item.id === id);
    if (!current) return;
    const value = !current.is_favorite;
    set({ items: before.map((item) => item.id === id ? { ...item, is_favorite: value } : item), error: null });
    if (demoMode) return;
    try {
      const updated = keepPreview(await itemsApi.favorite(id, value), current);
      set((state) => ({ items: state.items.map((item) => item.id === id ? updated : item) }));
    } catch (error) { set({ items: before, error: message(error) }); }
  },
  toggleArchive: async (id) => {
    const before = get().items;
    const current = before.find((item) => item.id === id);
    if (!current) return;
    const value = !current.is_archived;
    set({ items: before.map((item) => item.id === id ? { ...item, is_archived: value } : item), error: null });
    if (demoMode) return;
    try {
      const updated = keepPreview(await itemsApi.archive(id, value), current);
      set((state) => ({ items: state.items.map((item) => item.id === id ? updated : item), notice: value ? 'Item archived' : 'Item restored' }));
    } catch (error) { set({ items: before, error: message(error) }); }
  },
  deleteItem: async (id) => {
    const before = get().items;
    set({ items: before.filter((item) => item.id !== id), error: null });
    if (demoMode) return;
    try { await itemsApi.remove(id); set({ notice: 'Item deleted' }); }
    catch (error) { set({ items: before, error: message(error) }); throw error; }
  },
  retryProcessing: async (id) => {
    try {
      await itemsApi.retryProcessing(id);
      set({ notice: 'Processing queued', error: null });
      await get().initialize(true);
    } catch (error) {
      set({ error: message(error) });
      throw error;
    }
  },
  createCategory: async (name, color) => {
    try {
      const category = demoMode ? {
        id: crypto.randomUUID(), name: name.trim(), color, icon: 'folder', description: null,
        item_count: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      } : await categoriesApi.create({ name: name.trim(), color, icon: 'folder' });
      set((state) => ({ categories: [...state.categories, category], notice: 'Category created', error: null }));
    } catch (error) { set({ error: message(error) }); throw error; }
  },
  deleteCategory: async (id) => {
    const before = get().categories;
    const beforeItems = get().items;
    set((state) => ({ categories: before.filter((item) => item.id !== id), items: state.items.map((item) => item.category_id === id ? { ...item, category_id: null } : item) }));
    if (demoMode) return;
    try { await categoriesApi.remove(id); set({ notice: 'Category deleted' }); }
    catch (error) { set({ categories: before, items: beforeItems, error: message(error) }); }
  },
  deleteTag: async (id) => {
    const before = get().tags;
    const beforeItems = get().items;
    set((state) => ({ tags: before.filter((tag) => tag.id !== id), items: state.items.map((item) => ({ ...item, tags: item.tags.filter((tag) => tag.id !== id) })) }));
    if (demoMode) return;
    try { await tagsApi.remove(id); set({ notice: 'Tag deleted' }); }
    catch (error) { set({ tags: before, items: beforeItems, error: message(error) }); }
  },
}));
