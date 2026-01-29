import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Search, Grid, List, Plus, Filter, X } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'
import { LinkSource } from '../types'
import LinkCard from './LinkCard'

export default function LinkList() {
  const { categories, getFilteredLinks } = useLinkStore()
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [sourceFilter, setSourceFilter] = useState<LinkSource | ''>('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showFilters, setShowFilters] = useState(false)

  const filteredLinks = useMemo(() => {
    return getFilteredLinks({
      search,
      categoryId: categoryFilter || undefined,
      source: sourceFilter || undefined,
      showArchived: false
    })
  }, [search, categoryFilter, sourceFilter, getFilteredLinks])

  const hasFilters = categoryFilter || sourceFilter

  const clearFilters = () => {
    setCategoryFilter('')
    setSourceFilter('')
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Links</h1>
          <p className="text-gray-600">{filteredLinks.length} links found</p>
        </div>
        <Link
          to="/add"
          className="inline-flex items-center gap-2 gradient-memora text-white px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-all shadow-lg shadow-memora-500/25"
        >
          <Plus className="w-4 h-4" />
          Add Link
        </Link>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search links..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-10"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
              showFilters || hasFilters
                ? 'bg-memora-50 border-memora-200 text-memora-700'
                : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filters
            {hasFilters && (
              <span className="w-5 h-5 bg-memora-600 text-white text-xs rounded-full flex items-center justify-center">
                {(categoryFilter ? 1 : 0) + (sourceFilter ? 1 : 0)}
              </span>
            )}
          </button>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md transition-all ${
                viewMode === 'grid' ? 'bg-white shadow-sm text-memora-600' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-md transition-all ${
                viewMode === 'list' ? 'bg-white shadow-sm text-memora-600' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter Options */}
        {showFilters && (
          <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="input-field w-auto"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>

            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value as LinkSource | '')}
              className="input-field w-auto"
            >
              <option value="">All Sources</option>
              {Object.values(LinkSource).map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>

            {hasFilters && (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
              >
                <X className="w-4 h-4" />
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Links */}
      {filteredLinks.length > 0 ? (
        <div className={
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        }>
          {filteredLinks.map(link => (
            <LinkCard key={link.id} link={link} compact={viewMode === 'list'} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-12 text-center">
          <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No links found</h3>
          <p className="text-gray-500 mb-4">
            {search || hasFilters
              ? 'Try adjusting your search or filters'
              : 'Start by adding your first link'}
          </p>
          {!search && !hasFilters && (
            <Link
              to="/add"
              className="inline-flex items-center gap-2 text-memora-600 hover:text-memora-700 font-medium"
            >
              <Plus className="w-4 h-4" />
              Add your first link
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
