import {
  Archive,
  ArrowLeft,
  Calendar,
  Check,
  ExternalLink,
  FileText,
  Globe2,
  Image as ImageIcon,
  Link2,
  Pencil,
  RotateCcw,
  Star,
  Trash2,
  X,
} from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useLibraryStore } from '../store/libraryStore';

const icons = { link: Link2, screenshot: ImageIcon, text: FileText };

export default function ItemDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const store = useLibraryStore();
  const item = store.items.find((record) => record.id === id);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(item?.title ?? '');
  const [notes, setNotes] = useState(item?.notes ?? '');
  const [categoryId, setCategoryId] = useState(item?.category_id ?? '');

  if (!item) {
    return (
      <div className="page detail-page">
        <Link to="/" className="back-link"><ArrowLeft size={17} /> Library</Link>
        <section className="empty-state"><h1>Item not found</h1></section>
      </div>
    );
  }

  const TypeIcon = icons[item.type];
  const category = store.categories.find((record) => record.id === item.category_id);
  const previewUrl = item.metadata?.preview_url as string | undefined;

  const save = (event: FormEvent) => {
    event.preventDefault();
    store.updateItem(item.id, {
      expected_revision: item.revision,
      title: title || null,
      notes: notes || null,
      category_id: categoryId || null,
    });
    setEditing(false);
  };

  return (
    <div className="page detail-page">
      <Link to={item.is_archived ? '/archive' : '/'} className="back-link">
        <ArrowLeft size={17} /> Back
      </Link>
      <header className="detail-header">
        <div>
          <span className={`type-label ${item.type}`}><TypeIcon size={14} /> {item.type}</span>
          <h1>{item.title || item.source_domain || 'Untitled capture'}</h1>
          <div className="detail-subline">
            <span><Calendar size={15} /> {new Date(item.created_at).toLocaleDateString()}</span>
            {item.source_domain && <span><Globe2 size={15} /> {item.source_domain}</span>}
            {category && <span className="category-dot"><i style={{ background: category.color }} />{category.name}</span>}
          </div>
        </div>
        <div className="detail-actions">
          <button
            className={`icon-button${item.is_favorite ? ' selected' : ''}`}
            type="button"
            onClick={() => store.toggleFavorite(item.id)}
            title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star size={19} fill={item.is_favorite ? 'currentColor' : 'none'} />
          </button>
          <button className="button secondary" type="button" onClick={() => setEditing(true)}>
            <Pencil size={17} /> Edit
          </button>
          {item.url && (
            <a className="button primary" href={item.url} target="_blank" rel="noreferrer">
              Open <ExternalLink size={17} />
            </a>
          )}
        </div>
      </header>

      <div className="detail-layout">
        <article className="detail-content">
          {previewUrl && (
            <figure className="detail-image">
              <img src={previewUrl} alt={`Captured screen: ${item.title || 'Untitled capture'}`} />
            </figure>
          )}
          {item.summary && (
            <section className="content-section summary-section">
              <span className="section-label">Summary</span>
              <p>{item.summary}</p>
            </section>
          )}
          {item.raw_text && (
            <section className="content-section">
              <span className="section-label">Captured text</span>
              <p className="captured-text">{item.raw_text}</p>
            </section>
          )}
          {item.description && (
            <section className="content-section">
              <span className="section-label">Description</span>
              <p>{item.description}</p>
            </section>
          )}
          {item.notes && (
            <section className="content-section notes-section">
              <span className="section-label">Notes</span>
              <p>{item.notes}</p>
            </section>
          )}
          {item.extracted_text && (
            <details className="extracted-text">
              <summary>Extracted text</summary>
              <p>{item.extracted_text}</p>
            </details>
          )}
        </article>

        <aside className="detail-aside" aria-label="Item information">
          <section>
            <span className="section-label">Tags</span>
            <div className="item-tags large">
              {item.tags.length ? item.tags.map((tag) => <span key={tag.id}>#{tag.name}</span>) : <em>None</em>}
            </div>
          </section>
          <section>
            <span className="section-label">Processing</span>
            <div className={`status-row ${item.processing_status}`}>
              <i />
              <span>{item.processing_status}</span>
            </div>
          </section>
          <section className="aside-actions">
            <button type="button" onClick={() => store.toggleArchive(item.id)}>
              {item.is_archived ? <RotateCcw size={17} /> : <Archive size={17} />}
              {item.is_archived ? 'Restore item' : 'Archive item'}
            </button>
            <button
              type="button"
              className="danger"
              onClick={() => {
                if (window.confirm('Delete this item?')) {
                  store.deleteItem(item.id);
                  navigate('/');
                }
              }}
            >
              <Trash2 size={17} /> Delete item
            </button>
          </section>
        </aside>
      </div>

      {editing && (
        <div className="dialog-layer" role="presentation" onMouseDown={() => setEditing(false)}>
          <section
            className="edit-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="dialog-header">
              <h2 id="edit-title">Edit item</h2>
              <button className="icon-button" type="button" onClick={() => setEditing(false)}>
                <X size={20} /><span className="sr-only">Close</span>
              </button>
            </header>
            <form className="capture-form" onSubmit={save}>
              <label className="field"><span>Title</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
              <label className="field"><span>Category</span><select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">None</option>{store.categories.map((record) => <option key={record.id} value={record.id}>{record.name}</option>)}</select></label>
              <label className="field"><span>Notes</span><textarea rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
              <footer className="dialog-actions">
                <button className="button secondary" type="button" onClick={() => setEditing(false)}>Cancel</button>
                <button className="button primary" type="submit"><Check size={17} /> Save</button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
