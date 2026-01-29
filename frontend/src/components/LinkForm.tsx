import { useState, useEffect } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Link2, Image, ArrowLeft, Sparkles, X, Plus } from 'lucide-react'
import { useLinkStore } from '../store/linkStore'
import { LinkSource } from '../types'

type FormMode = 'url' | 'screenshot'

export default function LinkForm() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { links, categories, tags, addLink, updateLink } = useLinkStore()

  const isEditing = !!id
  const existingLink = isEditing ? links.find(l => l.id === id) : null

  const [mode, setMode] = useState<FormMode>(searchParams.get('type') === 'screenshot' ? 'screenshot' : 'url')
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (existingLink) {
      setUrl(existingLink.url || '')
      setTitle(existingLink.title)
      setDescription(existingLink.description || '')
      setCategoryId(existingLink.categoryId || '')
      setSelectedTags(existingLink.tags.map(t => t.name))
      setNotes(existingLink.notes || '')
      setMode(existingLink.source === LinkSource.SCREENSHOT ? 'screenshot' : 'url')
    }
  }, [existingLink])

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase()
    if (tag && !selectedTags.includes(tag)) {
      setSelectedTags([...selectedTags, tag])
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    setSelectedTags(selectedTags.filter(t => t !== tag))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      if (isEditing && existingLink) {
        updateLink(existingLink.id, {
          title,
          description,
          categoryId: categoryId || undefined,
          tags: selectedTags,
          notes
        })
      } else {
        addLink({
          url: mode === 'url' ? url : undefined,
          title: title || (mode === 'url' ? new URL(url).hostname : 'Screenshot'),
          description,
          source: mode === 'screenshot' ? LinkSource.SCREENSHOT : LinkSource.ARTICLE,
          categoryId: categoryId || undefined,
          tags: selectedTags,
          notes
        })
      }
      navigate('/links')
    } catch (error) {
      console.error('Error saving link:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const suggestedTags = tags
    .filter(t => !selectedTags.includes(t.name))
    .filter(t => !tagInput || t.name.includes(tagInput.toLowerCase()))
    .slice(0, 5)

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? 'Edit Link' : 'Add New Link'}
        </h1>
      </div>

      {/* Mode Toggle (only for new links) */}
      {!isEditing && (
        <div className="bg-white rounded-xl p-2 mb-6 flex gap-2">
          <button
            type="button"
            onClick={() => setMode('url')}
            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-all ${
              mode === 'url'
                ? 'bg-memora-100 text-memora-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Link2 className="w-5 h-5" />
            URL / Link
          </button>
          <button
            type="button"
            onClick={() => setMode('screenshot')}
            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-all ${
              mode === 'screenshot'
                ? 'bg-memora-100 text-memora-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Image className="w-5 h-5" />
            Screenshot
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-6">
        {/* URL Input */}
        {mode === 'url' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              URL *
            </label>
            <div className="relative">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                className="input-field pr-24"
                required={mode === 'url' && !isEditing}
                disabled={isEditing}
              />
              {!isEditing && url && (
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center gap-1 px-3 py-1 bg-memora-100 text-memora-700 rounded-md text-sm font-medium hover:bg-memora-200 transition-all"
                >
                  <Sparkles className="w-3 h-3" />
                  Parse
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Paste a URL and we'll automatically extract the title and description
            </p>
          </div>
        )}

        {/* Screenshot Upload */}
        {mode === 'screenshot' && !isEditing && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Screenshot
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-memora-400 transition-all cursor-pointer">
              <Image className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 mb-1">Click to upload or drag and drop</p>
              <p className="text-xs text-gray-500">PNG, JPG up to 10MB</p>
            </div>
          </div>
        )}

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a title"
            className="input-field"
            required
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add a description..."
            rows={3}
            className="input-field resize-none"
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Category
          </label>
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="input-field"
          >
            <option value="">Select a category</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {selectedTags.map(tag => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2.5 py-1 bg-memora-100 text-memora-700 rounded-full text-sm"
              >
                #{tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-memora-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="relative">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddTag()
                }
              }}
              placeholder="Add tags..."
              className="input-field"
            />
            {tagInput && (
              <button
                type="button"
                onClick={handleAddTag}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-memora-600 hover:text-memora-700"
              >
                <Plus className="w-5 h-5" />
              </button>
            )}
          </div>
          {suggestedTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {suggestedTags.map(tag => (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => setSelectedTags([...selectedTags, tag.name])}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-all"
                >
                  + {tag.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Personal Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add personal notes..."
            rows={3}
            className="input-field resize-none"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex-1 btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-1 btn-primary gradient-memora disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : isEditing ? 'Update Link' : 'Save Link'}
          </button>
        </div>
      </form>
    </div>
  )
}
