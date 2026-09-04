import { formatDistanceToNow } from 'date-fns';
import {
  Archive,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Link2,
  RotateCcw,
  Star,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useLibraryStore } from '../store/libraryStore';
import type { Item } from '../types/api';

const typeIcons = { link: Link2, screenshot: ImageIcon, text: FileText };

export default function ItemCard({ item, compact = false }: { item: Item; compact?: boolean }) {
  const toggleFavorite = useLibraryStore((state) => state.toggleFavorite);
  const toggleArchive = useLibraryStore((state) => state.toggleArchive);
  const TypeIcon = typeIcons[item.type];
  const previewUrl = item.metadata?.preview_url as string | undefined;

  return (
    <article className={`item-card ${compact ? 'compact' : ''}`}>
      {item.type === 'screenshot' && previewUrl && (
        <Link to={`/items/${item.id}`} className="item-preview" tabIndex={-1} aria-hidden="true">
          <img src={previewUrl} alt="" />
        </Link>
      )}
      <div className="item-card-body">
        <div className="item-meta-row">
          <span className={`type-label ${item.type}`}>
            <TypeIcon size={14} />
            {item.type}
          </span>
          {item.processing_status === 'processing' || item.processing_status === 'pending' ? (
            <span className="processing-label">
              <span className="processing-spinner" />
              {item.processing_status === 'pending' ? 'Queued' : 'Processing'}
            </span>
          ) : null}
          <span className="item-age">
            {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
          </span>
        </div>

        <h2>
          <Link to={`/items/${item.id}`}>
            {item.title || item.source_domain || 'Untitled capture'}
          </Link>
        </h2>
        {item.type === 'text' ? (
          <blockquote>{item.raw_text}</blockquote>
        ) : (
          <p>{item.summary || item.description || item.url}</p>
        )}

        <div className="item-tags" aria-label="Tags">
          {item.tags.slice(0, 3).map((tag) => (
            <span key={tag.id}>#{tag.name}</span>
          ))}
        </div>

        <footer className="item-card-footer">
          <span className="source-label">
            {item.source_domain || item.source || 'Personal note'}
            {item.type === 'link' && <ExternalLink size={13} />}
          </span>
          <span className="card-actions">
            <button
              type="button"
              className={item.is_favorite ? 'active' : ''}
              onClick={() => toggleFavorite(item.id)}
              title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            >
              <Star size={17} fill={item.is_favorite ? 'currentColor' : 'none'} />
              <span className="sr-only">
                {item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
              </span>
            </button>
            <button
              type="button"
              onClick={() => toggleArchive(item.id)}
              title={item.is_archived ? 'Restore' : 'Archive'}
            >
              {item.is_archived ? <RotateCcw size={17} /> : <Archive size={17} />}
              <span className="sr-only">{item.is_archived ? 'Restore' : 'Archive'}</span>
            </button>
          </span>
        </footer>
      </div>
    </article>
  );
}
