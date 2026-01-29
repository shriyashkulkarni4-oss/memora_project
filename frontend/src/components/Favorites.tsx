import { Link } from 'react-router-dom'
import { Star, Plus } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'
import LinkCard from './LinkCard'

export default function Favorites() {
  const { getFavorites } = useLinkStore()
  const favorites = getFavorites()

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Star className="w-6 h-6 text-amber-500" />
          Favorites
        </h1>
        <p className="text-gray-600">Your starred links</p>
      </div>

      {/* Links Grid */}
      {favorites.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {favorites.map(link => (
            <LinkCard key={link.id} link={link} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-12 text-center">
          <Star className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No favorites yet</h3>
          <p className="text-gray-500 mb-4">Star your important links to see them here</p>
          <Link
            to="/links"
            className="inline-flex items-center gap-2 text-memora-600 hover:text-memora-700 font-medium"
          >
            Browse links →
          </Link>
        </div>
      )}
    </div>
  )
}
