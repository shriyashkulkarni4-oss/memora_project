import { Link } from 'react-router-dom'
import { Link2, Star, Archive, Clock, Plus, ArrowRight, Sparkles, FolderOpen } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'
import LinkCard from './LinkCard'

export default function Dashboard() {
  const { categories, tags, getStats, getRecentLinks } = useLinkStore()
  const stats = getStats()
  const recentLinks = getRecentLinks(4)

  const statCards = [
    { label: 'Total Links', value: stats.totalLinks, icon: Link2, color: 'bg-blue-500' },
    { label: 'Favorites', value: stats.favoriteLinks, icon: Star, color: 'bg-amber-500' },
    { label: 'Pending AI', value: stats.pendingProcessing, icon: Sparkles, color: 'bg-purple-500' },
    { label: 'Archived', value: stats.archivedLinks, icon: Archive, color: 'bg-gray-500' },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Memora</h1>
        <p className="text-gray-600">Your smart bookmark & link management hub</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl p-5 shadow-sm card-hover">
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900">{value}</span>
            </div>
            <p className="text-sm text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl p-6 shadow-sm mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            to="/add"
            className="flex items-center gap-3 p-4 rounded-lg bg-memora-50 hover:bg-memora-100 text-memora-700 transition-all"
          >
            <Plus className="w-5 h-5" />
            <span className="font-medium">Add Link</span>
          </Link>
          <Link
            to="/add?type=screenshot"
            className="flex items-center gap-3 p-4 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 transition-all"
          >
            <Sparkles className="w-5 h-5" />
            <span className="font-medium">Add Screenshot</span>
          </Link>
          <Link
            to="/favorites"
            className="flex items-center gap-3 p-4 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 transition-all"
          >
            <Star className="w-5 h-5" />
            <span className="font-medium">Favorites</span>
          </Link>
          <Link
            to="/categories"
            className="flex items-center gap-3 p-4 rounded-lg bg-green-50 hover:bg-green-100 text-green-700 transition-all"
          >
            <FolderOpen className="w-5 h-5" />
            <span className="font-medium">Categories</span>
          </Link>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Recent Links */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-gray-400" />
              Recent Links
            </h2>
            <Link
              to="/links"
              className="text-sm text-memora-600 hover:text-memora-700 font-medium flex items-center gap-1"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="space-y-4">
            {recentLinks.length > 0 ? (
              recentLinks.map(link => (
                <LinkCard key={link.id} link={link} compact />
              ))
            ) : (
              <div className="bg-white rounded-xl p-8 text-center">
                <Link2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 mb-4">No links saved yet</p>
                <Link
                  to="/add"
                  className="inline-flex items-center gap-2 text-memora-600 hover:text-memora-700 font-medium"
                >
                  <Plus className="w-4 h-4" />
                  Add your first link
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Categories */}
          <div className="bg-white rounded-xl p-5 shadow-sm">
            <h3 className="font-semibold text-gray-900 mb-4">Categories</h3>
            <div className="space-y-2">
              {categories.slice(0, 5).map(category => (
                <Link
                  key={category.id}
                  to={`/links?category=${category.id}`}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    <span className="text-sm text-gray-700">{category.name}</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {stats.categoryCounts.find(c => c.categoryId === category.id)?.count || 0}
                  </span>
                </Link>
              ))}
            </div>
            <Link
              to="/categories"
              className="block mt-3 text-sm text-memora-600 hover:text-memora-700 font-medium"
            >
              Manage categories →
            </Link>
          </div>

          {/* Popular Tags */}
          <div className="bg-white rounded-xl p-5 shadow-sm">
            <h3 className="font-semibold text-gray-900 mb-4">Popular Tags</h3>
            <div className="flex flex-wrap gap-2">
              {tags.slice(0, 8).map(tag => (
                <Link
                  key={tag.id}
                  to={`/links?tag=${tag.name}`}
                  className="tag"
                  style={{
                    backgroundColor: `${tag.color}15`,
                    color: tag.color
                  }}
                >
                  #{tag.name}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
