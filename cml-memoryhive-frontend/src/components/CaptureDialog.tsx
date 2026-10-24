import {
  AlertCircle,
  ChevronDown,
  FileText,
  Files,
  Image as ImageIcon,
  Link2,
  Upload,
  X,
} from 'lucide-react';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLibraryStore } from '../store/libraryStore';
import type { ItemType } from '../types/api';
import TagPicker from './TagPicker';

const modes: { value: ItemType; label: string; icon: typeof Link2 }[] = [
  { value: 'link', label: 'Link', icon: Link2 },
  { value: 'document', label: 'Document', icon: Files },
  { value: 'screenshot', label: 'Screenshot', icon: ImageIcon },
  { value: 'text', label: 'Text', icon: FileText },
];

function normalizeTag(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function mergePendingTags(selected: string[], pending: string) {
  const next = new Set(selected.map(normalizeTag).filter(Boolean));
  pending.split(',').map(normalizeTag).filter(Boolean).forEach((tag) => next.add(tag));
  return [...next].sort();
}

export default function CaptureDialog() {
  const open = useLibraryStore((state) => state.captureOpen);
  const close = useLibraryStore((state) => state.setCaptureOpen);
  const createItem = useLibraryStore((state) => state.createItem);
  const categories = useLibraryStore((state) => state.categories);
  const availableTags = useLibraryStore((state) => state.tags);
  const uploadProgress = useLibraryStore((state) => state.uploadProgress);
  const navigate = useNavigate();
  const firstField = useRef<HTMLElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const pointerSubmit = useRef(false);
  const [type, setType] = useState<ItemType>('link');
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [pendingTagInput, setPendingTagInput] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [notes, setNotes] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const timer = window.setTimeout(() => firstField.current?.focus(), 20);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('keydown', onKeyDown);
      previous?.focus();
    };
  }, [close, open]);

  if (!open) return null;

  const reset = () => {
    setUrl('');
    setText('');
    setTitle('');
    setTags([]);
    setPendingTagInput('');
    setCategoryId('');
    setNotes('');
    setFile(null);
    setDetailsOpen(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const submittedTags = mergePendingTags(tags, pendingTagInput);
      const item = await createItem({
        type,
        url: type === 'link' ? url : undefined,
        raw_text: type === 'text' ? text : undefined,
        title: title || (type === 'text' ? text.slice(0, 72) : undefined),
        notes: notes || undefined,
        category_id: categoryId || undefined,
        tags: submittedTags,
      }, file ?? undefined);
      reset();
      navigate(`/items/${item.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to save item');
    } finally {
      setBusy(false);
    }
  };

  const requestSave = () => formRef.current?.requestSubmit();

  return (
    <div className="dialog-layer" role="presentation" onMouseDown={() => close(false)}>
      <section
        className="capture-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="capture-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="dialog-header">
          <div>
            <span className="eyebrow">New capture</span>
            <h2 id="capture-title">Save to Memoryhive</h2>
          </div>
          <button className="icon-button" type="button" onClick={() => close(false)}>
            <X size={20} />
            <span className="sr-only">Close capture</span>
          </button>
        </header>

        <div className="capture-tabs" role="tablist" aria-label="Capture type">
          {modes.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={type === value}
              className={type === value ? 'active' : ''}
              onClick={() => setType(value)}
            >
              <Icon size={17} />
              {label}
            </button>
          ))}
        </div>

        <form ref={formRef} className="capture-form" onSubmit={submit}>
          {error && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
          {uploadProgress !== null && (
            <div className="upload-progress" role="progressbar" aria-label="Screenshot upload" aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadProgress}>
              <span style={{ width: `${uploadProgress}%` }} />
              <small>{uploadProgress}% uploaded</small>
            </div>
          )}
          {type === 'link' && (
            <label className="field">
              <span>URL</span>
              <div className="input-with-icon">
                <Link2 size={18} />
                <input
                  ref={(node) => {
                    firstField.current = node;
                  }}
                  type="url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://"
                  required
                />
              </div>
            </label>
          )}

          {type === 'text' && (
            <label className="field">
              <span>Text</span>
              <textarea
                ref={(node) => {
                  firstField.current = node;
                }}
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={7}
                placeholder="Write or paste text"
                required
              />
            </label>
          )}

          {type === 'document' && (
            <label className={`drop-field${file ? ' has-file' : ''}`}>
              <input
                ref={(node) => {
                  firstField.current = node;
                }}
                type="file"
                accept="application/pdf,.pdf,text/plain,.txt,text/markdown,.md"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
              {file ? <Files size={24} /> : <Upload size={24} />}
              <strong>{file?.name || 'Choose a document'}</strong>
              <span>{file ? `${Math.ceil(file.size / 1024)} KB` : 'PDF (multi-page with OCR) or Text document'}</span>
            </label>
          )}

          {type === 'screenshot' && (
            <label className={`drop-field${file ? ' has-file' : ''}`}>
              <input
                ref={(node) => {
                  firstField.current = node;
                }}
                type="file"
                accept="image/png,image/jpeg,image/gif,image/webp"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
              {file ? <ImageIcon size={24} /> : <Upload size={24} />}
              <strong>{file?.name || 'Choose an image'}</strong>
              <span>{file ? `${Math.ceil(file.size / 1024)} KB` : 'PNG, JPEG, GIF, or WebP'}</span>
            </label>
          )}

          <label className="field">
            <span>Title <small>Optional</small></span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={500} />
          </label>

          <button
            className="details-toggle"
            type="button"
            aria-expanded={detailsOpen}
            onClick={() => setDetailsOpen((value) => !value)}
          >
            Details
            <ChevronDown size={17} className={detailsOpen ? 'rotated' : ''} />
          </button>

          {detailsOpen && (
            <div className="optional-fields">
              <TagPicker
                selected={tags}
                available={availableTags}
                onChange={setTags}
                onInputChange={setPendingTagInput}
              />
              <label className="field">
                <span>Category</span>
                <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                  <option value="">None</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
              </label>
              <label className="field full">
                <span>Notes</span>
                <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
              </label>
            </div>
          )}

          <footer className="dialog-actions">
            <button className="button secondary" type="button" disabled={busy} onClick={() => close(false)}>Cancel</button>
            <button
              className="button primary"
              type="button"
              disabled={busy}
              onMouseDown={(event) => {
                if (event.button !== 0) return;
                pointerSubmit.current = true;
                event.preventDefault();
                requestSave();
              }}
              onClick={() => {
                if (pointerSubmit.current) {
                  pointerSubmit.current = false;
                  return;
                }
                requestSave();
              }}
            >
              {busy ? 'Saving' : 'Save item'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
