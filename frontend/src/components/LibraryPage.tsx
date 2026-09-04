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
import { useMemo, useState } from 'react';
import { useLibraryStore } from '../store/libraryStore';
import type { ItemType } from '../types/api';
import ItemCard from './ItemCard';

type LibraryMode = 'library' | 'favorites' | 'archive';

const typeOptions: { value: ItemType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'link', label: 'Links' },
  { value: 'screenshot', label: 'Screenshots' },
  { value: 'text', label: 'Text' },
];

export default function LibraryPage({ mode = 'library' }: { mode?: LibraryMode }) {
  const store = useLibraryStore();
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState('newest');
  const pageTitle = mode === 'favorites' ? 'Favorites' : mode === 'archive' ? 'Archive' : 'Library';

  const visibleItems = useMemo(() => {
    const query = store.query.trim().toLowerCase();
    const records = store.items.filter((item) => {
      if (mode === 'favorites' && (!item.is_favorite || item.is_archived)) return false;
      if (mode === 'archive' && !item.is_archived) return false;
      if (mode === 'library' && item.is_archived) return false;
      if (store.typeFilter !== 'all' && item.type !== store.typeFilter) return false;
      if (category !== 'all' && item.category_id !== category) return false;
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
  }, [category, mode, sort, store.items, store.query, store.typeFilter]);

  const activeItems = store.items.filter((item) => !item.is_archived);
  const pending = activeItems.filter((item) => ['pending', 'processing'].includes(item.processing_status)).length;
  const favorites = activeItems.filter((item) => item.is_favorite).length;

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

      {mode === 'library' && (
        <div className="library-summary" aria-label="Library summary">
          <span><strong>{activeItems.length}</strong> saved</span>
          <span><Star size={15} /> <strong>{favorites}</strong> favorites</span>
          <span><Sparkles size={15} /> <strong>{pending}</strong> processing</span>
          <span><Archive size={15} /> <strong>{store.items.length - activeItems.length}</strong> archived</span>
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
            onChange={(event) => store.setQuery(event.target.value)}
            placeholder="Search title, text, source, or tag"
          />
          {store.query && (
            <button type="button" onClick={() => store.setQuery('')} title="Clear search">
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
                className={store.typeFilter === option.value ? 'active' : ''}
                aria-pressed={store.typeFilter === option.value}
                onClick={() => store.setTypeFilter(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="select-controls">
            <label>
              <span className="sr-only">Category</span>
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="all">All categories</option>
                {store.categories.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
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
      </section>

      {visibleItems.length ? (
        <section className={`items-layout ${store.viewMode}`} aria-live="polite">
          {visibleItems.map((item) => (
            <ItemCard key={item.id} item={item} compact={store.viewMode === 'list'} />
          ))}
        </section>
      ) : (
        <section className="empty-state">
          <Search size={28} />
          <h2>No matching items</h2>
          <p>Adjust the current search or filters.</p>
          <button className="button secondary" type="button" onClick={() => {
            store.setQuery('');
            store.setTypeFilter('all');
            setCategory('all');
          }}>Clear filters</button>
        </section>
      )}
    </div>
  );
}
