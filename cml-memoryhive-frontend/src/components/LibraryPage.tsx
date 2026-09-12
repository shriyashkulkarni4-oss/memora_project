import {
  Archive,
  Grid2X2,
  List,
  Plus,
  Search,
  Sparkles,
  Star,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useLibraryStore } from '../store/libraryStore';
import type { Item, ItemType } from '../types/api';
import FilterPills, { type FilterPill } from './FilterPills';
import GroundedRecallPanel from './GroundedRecallPanel';
import ItemCard from './ItemCard';
import ResurfacingPanel from './ResurfacingPanel';

type LibraryMode = 'library' | 'favorites' | 'archive';
type SummaryFilter = 'saved' | 'favorites' | 'processing' | 'archived';

const typeOptions: { value: ItemType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'link', label: 'Links' },
  { value: 'screenshot', label: 'Screenshots' },
  { value: 'text', label: 'Text' },
];

const summaryLabels: Record<SummaryFilter, string> = {
  saved: 'Saved',
  favorites: 'Favorites',
  processing: 'Processing',
  archived: 'Archived',
};

function normalizeTag(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function uniqueTags(values: string[]) {
  return Array.from(new Set(values.map(normalizeTag).filter(Boolean)));
}

export default function LibraryPage({ mode = 'library' }: { mode?: LibraryMode }) {
  const store = useLibraryStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sort, setSort] = useState('newest');
  const query = store.query;
  const search = store.search;
  const pageTitle = mode === 'favorites' ? 'Favorites' : mode === 'archive' ? 'Archive' : 'Library';
  const requestedType = searchParams.get('type');
  const typeFilter = typeOptions.some((option) => option.value === requestedType) ? requestedType as ItemType : 'all';
  const category = searchParams.get('category') ?? 'all';
  const classification = searchParams.get('classification') ?? 'all';
  const topic = searchParams.get('topic') ?? 'all';
  const tagFilters = useMemo(() => uniqueTags(searchParams.getAll('tag')), [searchParams]);
  const requestedSummary = searchParams.get('summary');
  const summaryFilter = requestedSummary !== null && requestedSummary in summaryLabels ? requestedSummary as SummaryFilter : null;
  const effectiveSummaryFilter = mode === 'library' ? summaryFilter : null;

  const updateFilters = useCallback((updates: Record<string, string | string[] | null>) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      next.delete(key);
      if (Array.isArray(value)) value.forEach((entry) => next.append(key, entry));
      else if (value) next.set(key, value);
    });
    setSearchParams(next);
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => void search(query), 250);
    return () => window.clearTimeout(timer);
  }, [query, search]);

  useEffect(() => {
    const paramQuery = searchParams.get('q') ?? '';
    if (paramQuery !== store.query) store.setQuery(paramQuery);
  }, [searchParams, store]);

  useEffect(() => {
    if (typeFilter !== store.typeFilter) store.setTypeFilter(typeFilter);
  }, [store, typeFilter]);

  const applySummaryFilter = useCallback((item: Item) => {
    const current = effectiveSummaryFilter ?? (mode === 'favorites' ? 'favorites' : mode === 'archive' ? 'archived' : 'saved');
    if (current === 'favorites') return item.is_favorite && !item.is_archived;
    if (current === 'archived') return item.is_archived;
    if (current === 'processing') return !item.is_archived && ['pending', 'processing'].includes(item.processing_status);
    return !item.is_archived;
  }, [effectiveSummaryFilter, mode]);

  const visibleItems = useMemo(() => {
    const query = store.query.trim().toLowerCase();
    const records = (query && store.searchResults ? store.searchResults : store.items).filter((item) => {
      if (!applySummaryFilter(item)) return false;
      if (typeFilter !== 'all' && item.type !== typeFilter) return false;
      if (category !== 'all' && item.category_id !== category) return false;
      const enrichment = item.metadata?.enrichment as { classification?: string; topics?: string[] } | undefined;
      if (classification !== 'all' && enrichment?.classification !== classification) return false;
      if (topic !== 'all' && !enrichment?.topics?.includes(topic)) return false;
      if (tagFilters.length && !tagFilters.every((tag) => item.tags.some((itemTag) => itemTag.name === tag))) return false;
      if (!query) return true;
      return [
        item.title,
        item.description,
        item.summary,
        item.raw_text,
        item.extracted_text,
        item.url,
        item.source,
        ...item.tags.map((tag) => tag.name),
      ].some((value) => value?.toLowerCase().includes(query));
    });
    return records.sort((a, b) => {
      if (sort === 'oldest') return a.created_at.localeCompare(b.created_at);
      if (sort === 'title') return (a.title || '').localeCompare(b.title || '');
      return b.created_at.localeCompare(a.created_at);
    });
  }, [applySummaryFilter, category, classification, sort, store.items, store.query, store.searchResults, tagFilters, topic, typeFilter]);

  const activeItems = store.items.filter((item) => !item.is_archived);
  const pending = activeItems.filter((item) => ['pending', 'processing'].includes(item.processing_status)).length;
  const favorites = activeItems.filter((item) => item.is_favorite).length;
  const categoryLabel = store.categories.find((item) => item.id === category)?.name;
  const classificationOptions = Array.from(new Set(store.items.map((item) => (item.metadata?.enrichment as { classification?: string } | undefined)?.classification).filter((value): value is string => Boolean(value)))).sort();
  const topicOptions = Array.from(new Set(store.items.flatMap((item) => (item.metadata?.enrichment as { topics?: string[] } | undefined)?.topics || []))).sort();
  const activePills: FilterPill[] = [
    ...(store.query.trim() ? [{
      id: 'q',
      label: `Search: ${store.query.trim()}`,
      onRemove: () => {
        store.setQuery('');
        updateFilters({ q: null });
      },
    }] : []),
    ...(typeFilter !== 'all' ? [{
      id: 'type',
      label: typeOptions.find((option) => option.value === typeFilter)?.label ?? typeFilter,
      onRemove: () => updateFilters({ type: null }),
    }] : []),
    ...(category !== 'all' ? [{
      id: 'category',
      label: `Category: ${categoryLabel ?? 'Unknown'}`,
      onRemove: () => updateFilters({ category: null }),
    }] : []),
    ...(classification !== 'all' ? [{ id: 'classification', label: `Classification: ${classification}`, onRemove: () => updateFilters({ classification: null }) }] : []),
    ...(topic !== 'all' ? [{ id: 'topic', label: `Topic: ${topic}`, onRemove: () => updateFilters({ topic: null }) }] : []),
    ...tagFilters.map((tag) => ({
      id: `tag:${tag}`,
      label: `#${tag}`,
      onRemove: () => updateFilters({ tag: tagFilters.filter((value) => value !== tag) }),
    })),
    ...(effectiveSummaryFilter ? [{
      id: 'summary',
      label: summaryLabels[effectiveSummaryFilter],
      onRemove: () => updateFilters({ summary: null }),
    }] : []),
  ];

  if (store.isLoading && !store.initialized) {
    return <div className="page"><section className="empty-state" aria-label="Loading library"><span className="brand-loader" /></section></div>;
  }

  return (
    <div className="page library-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Personal knowledge</span>
          <h1>{pageTitle}</h1>
          <p>{visibleItems.length} {visibleItems.length === 1 ? 'item' : 'items'}</p>
        </div>
        <button className="button primary" type="button" onClick={() => store.setCaptureOpen(true)}>
          <Plus size={18} />
          Capture
        </button>
      </header>
      {mode === 'library' ? <GroundedRecallPanel /> : null}
      {mode === 'library' ? <ResurfacingPanel /> : null}

      {mode === 'library' && (
        <div className="library-summary" aria-label="Library summary">
          <button type="button" className={summaryFilter === null || summaryFilter === 'saved' ? 'active' : ''} onClick={() => updateFilters({ summary: null })}>
            <strong>{activeItems.length}</strong> saved
          </button>
          <button type="button" className={summaryFilter === 'favorites' ? 'active' : ''} onClick={() => updateFilters({ summary: 'favorites' })}>
            <Star size={15} /> <strong>{favorites}</strong> favorites
          </button>
          <button type="button" className={summaryFilter === 'processing' ? 'active' : ''} onClick={() => updateFilters({ summary: 'processing' })}>
            <Sparkles size={15} /> <strong>{pending}</strong> processing
          </button>
          <button type="button" className={summaryFilter === 'archived' ? 'active' : ''} onClick={() => updateFilters({ summary: 'archived' })}>
            <Archive size={15} /> <strong>{store.items.length - activeItems.length}</strong> archived
          </button>
        </div>
      )}

      <section className="library-controls" aria-label="Library filters">
        <label className="search-box">
          <Search size={19} aria-hidden="true" />
          <span className="sr-only">Search library</span>
          <input
            id="library-search"
            type="search"
            value={store.query}
            onChange={(event) => {
              store.setQuery(event.target.value);
              updateFilters({ q: event.target.value || null });
            }}
            placeholder="Search title, text, source, or tag"
          />
          {store.query && (
            <button type="button" onClick={() => {
              store.setQuery('');
              updateFilters({ q: null });
            }} title="Clear search">
              <X size={17} />
              <span className="sr-only">Clear search</span>
            </button>
          )}
        </label>

        <div className="control-row">
          <div className="segmented" aria-label="Item type">
            {typeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={typeFilter === option.value ? 'active' : ''}
                aria-pressed={typeFilter === option.value}
                onClick={() => updateFilters({ type: option.value === 'all' ? null : option.value })}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="select-controls">
            <label>
              <span className="sr-only">Category</span>
              <select value={category} onChange={(event) => updateFilters({ category: event.target.value === 'all' ? null : event.target.value })}>
                <option value="all">All categories</option>
                {store.categories.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            {classificationOptions.length ? <label>
              <span className="sr-only">AI classification</span>
              <select value={classification} onChange={(event) => updateFilters({ classification: event.target.value === 'all' ? null : event.target.value })}>
                <option value="all">All classifications</option>
                {classificationOptions.map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </label> : null}
            {topicOptions.length ? <label>
              <span className="sr-only">AI topic</span>
              <select value={topic} onChange={(event) => updateFilters({ topic: event.target.value === 'all' ? null : event.target.value })}>
                <option value="all">All topics</option>
                {topicOptions.map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </label> : null}
            <label>
              <span className="sr-only">Sort</span>
              <select value={sort} onChange={(event) => setSort(event.target.value)}>
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="title">Title</option>
              </select>
            </label>
            <div className="view-toggle" aria-label="View style">
              <button
                type="button"
                className={store.viewMode === 'grid' ? 'active' : ''}
                onClick={() => store.setViewMode('grid')}
                title="Grid view"
              >
                <Grid2X2 size={17} />
                <span className="sr-only">Grid view</span>
              </button>
              <button
                type="button"
                className={store.viewMode === 'list' ? 'active' : ''}
                onClick={() => store.setViewMode('list')}
                title="List view"
              >
                <List size={18} />
                <span className="sr-only">List view</span>
              </button>
            </div>
          </div>
        </div>
        <FilterPills
          pills={activePills}
          onClear={activePills.length ? () => {
            store.setQuery('');
            updateFilters({ q: null, type: null, category: null, tag: null, summary: null });
          } : undefined}
        />
      </section>

      {visibleItems.length ? (
        <section className={`items-layout ${store.viewMode}`} aria-live="polite">
          {visibleItems.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              compact={store.viewMode === 'list'}
              onTagClick={(tag) => updateFilters({ tag: uniqueTags([...tagFilters, tag]) })}
            />
          ))}
        </section>
      ) : (
        <section className="empty-state">
          <Search size={28} />
          <h2>No matching items</h2>
          <p>Adjust the current search or filters.</p>
          <button className="button secondary" type="button" onClick={() => {
            store.setQuery('');
            updateFilters({ q: null, type: null, category: null, tag: null, summary: null });
          }}>Clear filters</button>
        </section>
      )}
    </div>
  );
}
