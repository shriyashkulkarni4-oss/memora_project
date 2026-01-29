import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderOpen, Plus, Edit, Trash2, X, Check } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'

const iconOptions = ['FolderOpen', 'Code', 'Brain', 'Briefcase', 'Palette', 'BookOpen', 'Rocket', 'Heart', 'Star', 'Zap']
const colorOptions = ['#3b82f6', '#8b5cf6', '#10b981', '#f43f5e', '#f59e0b', '#06b6d4', '#ec4899', '#6366f1', '#84cc16', '#14b8a6']

export default function Categories() {
  const { categories, addCategory, updateCategory, deleteCategory, getStats } = useLinkStore()
  const stats = getStats()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState(colorOptions[0])
  const [icon, setIcon] = useState(iconOptions[0])

  const resetForm = () => {
    setName('')
    setDescription('')
    setColor(colorOptions[0])
    setIcon(iconOptions[0])
    setShowForm(false)
    setEditingId(null)
  }

  const handleEdit = (cat: typeof categories[0]) => {
    setEditingId(cat.id)
    setName(cat.name)
    setDescription(cat.description || '')
    setColor(cat.color)
    setIcon(cat.icon)
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingId) {
      updateCategory(editingId, { name, description, color, icon })
    } else {
      addCategory({ name, description, color, icon })
    }
    resetForm()
  }

  const handleDelete = (id: string, categoryName: string) => {
    if (confirm(`Delete category "${categoryName}"? Links in this category will become uncategorized.`)) {
      deleteCategory(id)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
          <p className="text-gray-600">Organize your links into categories</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-2 gradient-memora text-white px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-all shadow-lg shadow-memora-500/25"
        >
          <Plus className="w-4 h-4" />
          New Category
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6 animate-fadeIn">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {editingId ? 'Edit Category' : 'New Category'}
            </h2>
            <button onClick={resetForm} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Tech & Development"
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
              <div className="flex gap-2">
                {colorOptions.map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={`w-8 h-8 rounded-full transition-all ${
                      color === c ? 'ring-2 ring-offset-2 ring-gray-400 scale-110' : ''
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={resetForm} className="flex-1 btn-secondary">
                Cancel
              </button>
              <button type="submit" className="flex-1 btn-primary gradient-memora">
                {editingId ? 'Update' : 'Create'} Category
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Categories List */}
      <div className="space-y-3">
        {categories.length > 0 ? (
          categories.map(category => {
            const linkCount = stats.categoryCounts.find(c => c.categoryId === category.id)?.count || 0
            return (
              <div
                key={category.id}
                className="bg-white rounded-xl p-4 shadow-sm flex items-center justify-between card-hover"
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${category.color}20` }}
                  >
                    <FolderOpen className="w-6 h-6" style={{ color: category.color }} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{category.name}</h3>
                    <p className="text-sm text-gray-500">
                      {linkCount} {linkCount === 1 ? 'link' : 'links'}
                      {category.description && ` · ${category.description}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/links?category=${category.id}`}
                    className="text-sm text-memora-600 hover:text-memora-700 font-medium"
                  >
                    View links →
                  </Link>
                  <button
                    onClick={() => handleEdit(category)}
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(category.id, category.name)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })
        ) : (
          <div className="bg-white rounded-xl p-12 text-center">
            <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No categories yet</h3>
            <p className="text-gray-500 mb-4">Create categories to organize your links</p>
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 text-memora-600 hover:text-memora-700 font-medium"
            >
              <Plus className="w-4 h-4" />
              Create your first category
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
