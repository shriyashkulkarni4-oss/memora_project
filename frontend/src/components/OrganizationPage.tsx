import { Folder, Plus, Tag, Trash2 } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useLibraryStore } from '../store/libraryStore';

const colors = ['#0f766e', '#2563eb', '#7c3aed', '#ea580c', '#ca8a04', '#be123c'];

export default function OrganizationPage() {
  const store = useLibraryStore();
  const [name, setName] = useState('');
  const [color, setColor] = useState(colors[0]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    try {
      await store.createCategory(name, color);
      setName('');
    } catch {
      // The store exposes the API error through the application message.
    }
  };

  return (
    <div className="page organize-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Library structure</span>
          <h1>Organize</h1>
          <p>Categories and tags</p>
        </div>
      </header>

      <section className="management-section" aria-labelledby="categories-heading">
        <div className="section-heading">
          <div><Folder size={19} /><h2 id="categories-heading">Categories</h2></div>
          <span>{store.categories.length}</span>
        </div>
        <form className="inline-create" onSubmit={create}>
          <label>
            <span className="sr-only">Category name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="New category" maxLength={100} />
          </label>
          <fieldset className="color-picker">
            <legend className="sr-only">Category color</legend>
            {colors.map((option) => (
              <label key={option} title={option}>
                <input type="radio" name="color" value={option} checked={color === option} onChange={() => setColor(option)} />
                <span style={{ background: option }} />
              </label>
            ))}
          </fieldset>
          <button className="button primary" type="submit"><Plus size={17} /> Add</button>
        </form>
        <div className="management-list">
          {store.categories.map((category) => (
            <div className="management-row" key={category.id}>
              <i className="category-swatch" style={{ background: category.color }} />
              <div><strong>{category.name}</strong><span>{category.description || 'No description'}</span></div>
              <span className="usage-count">{store.items.filter((item) => item.category_id === category.id).length} items</span>
              <button className="icon-button" type="button" title="Delete category" onClick={() => void store.deleteCategory(category.id)}>
                <Trash2 size={17} /><span className="sr-only">Delete {category.name}</span>
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="management-section" aria-labelledby="tags-heading">
        <div className="section-heading">
          <div><Tag size={19} /><h2 id="tags-heading">Tags</h2></div>
          <span>{store.tags.length}</span>
        </div>
        <div className="tag-management-grid">
          {store.tags.map((tag) => (
            <div key={tag.id} className="tag-management-item">
              <i style={{ background: tag.color }} />
              <strong>#{tag.name}</strong>
              <span>{store.items.filter((item) => item.tags.some((value) => value.id === tag.id)).length}</span>
              <button type="button" title="Delete tag" onClick={() => void store.deleteTag(tag.id)}>
                <Trash2 size={15} /><span className="sr-only">Delete {tag.name}</span>
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
