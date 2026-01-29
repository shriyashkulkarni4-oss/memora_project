import { Link } from 'react-router-dom'
import { Archive as ArchiveIcon } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'
import LinkCard from './LinkCard'

export default function Archive() {
  const { getArchived } = useLinkStore()
  const archived = getArchived()

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ArchiveIcon className="w-6 h-6 text-gray-500" />
          Archive
        </h1>
        <p className="text-gray-600">Your archived links</p>
      </div>

      {/* Links Grid */}
      {archived.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {archived.map(link => (
            <LinkCard key={link.id} link={link} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-12 text-center">
          <ArchiveIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Archive is empty</h3>
          <p className="text-gray-500 mb-4">Links you archive will appear here</p>
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
