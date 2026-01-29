import { Link as RouterLink } from 'react-router-dom'
import { Star, Archive, MoreVertical, ExternalLink, Edit, Trash2, Sparkles, Clock } from 'lucide-react'
import { useState } from 'react'
import { format } from 'date-fns'
import { Link, LinkSource } from '../types'
import { useLinkStore } from '../store/linkStore'

const sourceIcons: Record<LinkSource, string> = {
  twitter: '𝕏',
  linkedin: 'in',
  youtube: '▶',
  github: '⌘',
  article: '📄',
  news: '📰',
  screenshot: '🖼',
  manual: '🔗',
  other: '🌐'
}

const sourceColors: Record<LinkSource, string> = {
  twitter: 'bg-gray-900',
  linkedin: 'bg-blue-600',
  youtube: 'bg-red-600',
  github: 'bg-gray-800',
  article: 'bg-blue-500',
  news: 'bg-amber-500',
  screenshot: 'bg-indigo-500',
  manual: 'bg-gray-500',
  other: 'bg-gray-400'
}

interface LinkCardProps {
  link: Link
  compact?: boolean
}

export default function LinkCard({ link, compact = false }: LinkCardProps) {
  const [showMenu, setShowMenu] = useState(false)
  const { toggleFavorite, toggleArchive, deleteLink, categories } = useLinkStore()

  const category = categories.find(c => c.id === link.categoryId)

  const handleDelete = () => {
    if (confirm(`Delete "${link.title}"?`)) {
      deleteLink(link.id)
    }
    setShowMenu(false)
  }

  if (compact) {
    return (
      <div className="bg-white rounded-xl p-4 shadow-sm card-hover animate-fadeIn">
        <div className="flex items-start gap-3">
          {/* Source Icon */}
          <div className={`w-10 h-10 ${sourceColors[link.source]} rounded-lg flex items-center justify-center text-white text-sm font-bold flex-shrink-0`}>
            {sourceIcons[link.source]}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {link.url ? (
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-gray-900 hover:text-memora-600 truncate flex items-center gap-1"
                >
                  {link.title}
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
                </a>
              ) : (
                <span className="font-medium text-gray-900 truncate">{link.title}</span>
              )}
              {link.isFavorite && <Star className="w-4 h-4 text-amber-500 fill-amber-500 flex-shrink-0" />}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              {category && (
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: category.color }} />
                  {category.name}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {format(new Date(link.createdAt), 'MMM d')}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={() => toggleFavorite(link.id)}
              className={`p-2 rounded-lg transition-all ${
                link.isFavorite ? 'text-amber-500' : 'text-gray-400 hover:text-amber-500 hover:bg-amber-50'
              }`}
            >
              <Star className={`w-4 h-4 ${link.isFavorite ? 'fill-current' : ''}`} />
            </button>
            <RouterLink
              to={`/edit/${link.id}`}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
            >
              <Edit className="w-4 h-4" />
            </RouterLink>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden card-hover animate-fadeIn">
      {/* Screenshot Preview */}
      {link.screenshot?.fileUrl && (
        <div className="h-40 bg-gray-100 overflow-hidden">
          <img
            src={link.screenshot.fileUrl}
            alt={link.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 ${sourceColors[link.source]} rounded-lg flex items-center justify-center text-white text-sm font-bold`}>
            {sourceIcons[link.source]}
          </div>
          <div>
            <span className="text-xs font-medium text-gray-500 uppercase">{link.source}</span>
            <p className="text-xs text-gray-400">{format(new Date(link.createdAt), 'MMM d, yyyy')}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => toggleFavorite(link.id)}
            className={`p-2 rounded-lg transition-all ${
              link.isFavorite ? 'text-amber-500' : 'text-gray-400 hover:text-amber-500 hover:bg-amber-50'
            }`}
          >
            <Star className={`w-5 h-5 ${link.isFavorite ? 'fill-current' : ''}`} />
          </button>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border py-1 z-20">
                  <RouterLink
                    to={`/edit/${link.id}`}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowMenu(false)}
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </RouterLink>
                  <button
                    onClick={() => { toggleArchive(link.id); setShowMenu(false); }}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full"
                  >
                    <Archive className="w-4 h-4" />
                    {link.isArchived ? 'Unarchive' : 'Archive'}
                  </button>
                  <hr className="my-1" />
                  <button
                    onClick={handleDelete}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-1">
          {link.url ? (
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-memora-600 flex items-center gap-1"
            >
              {link.title}
              <ExternalLink className="w-4 h-4" />
            </a>
          ) : (
            link.title
          )}
        </h3>

        {link.description && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">{link.description}</p>
        )}

        {/* AI Summary */}
        {link.aiSummary && (
          <div className="bg-green-50 rounded-lg p-3 mb-3">
            <div className="flex items-center gap-1 text-green-700 text-xs font-medium mb-1">
              <Sparkles className="w-3 h-3" />
              AI Summary
            </div>
            <p className="text-sm text-gray-700 line-clamp-2">{link.aiSummary.summary}</p>
          </div>
        )}

        {/* Tags */}
        {link.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {link.tags.map(tag => (
              <span
                key={tag.id}
                className="tag"
                style={{
                  backgroundColor: `${tag.color}15`,
                  color: tag.color
                }}
              >
                #{tag.name}
              </span>
            ))}
          </div>
        )}

        {/* Status */}
        {link.status === 'pending' && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" />
            Pending AI processing
          </span>
        )}
      </div>

      {/* Footer */}
      {(link.readCount > 0 || category) && (
        <div className="px-4 py-3 border-t bg-gray-50 flex items-center justify-between text-xs text-gray-500">
          {category && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: category.color }} />
              {category.name}
            </span>
          )}
          {link.readCount > 0 && (
            <span>{link.readCount} visits</span>
          )}
        </div>
      )}
    </div>
  )
}
