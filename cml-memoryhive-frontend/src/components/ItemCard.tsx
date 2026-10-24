import { formatDistanceToNow } from 'date-fns';
import {
  Archive,
  Eye,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Link2,
  RotateCcw,
  Star,
} from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useLibraryStore } from '../store/libraryStore';
import type { Item } from '../types/api';
import ConfirmDialog from './ConfirmDialog';

const typeIcons = { link: Link2, screenshot: ImageIcon, text: FileText };
type CardConfirmation = 'favorite' | 'archive' | null;

export default function ItemCard({
  item,
  compact = false,
  index = 0,
  onTagClick,
}: {
  item: Item;
  compact?: boolean;
  index?: number;
  onTagClick?: (tag: string) => void;
}) {
  const toggleFavorite = useLibraryStore((state) => state.toggleFavorite);
  const toggleArchive = useLibraryStore((state) => state.toggleArchive);
  const [confirmation, setConfirmation] = useState<CardConfirmation>(null);
  const [busy, setBusy] = useState(false);
  const TypeIcon = typeIcons[item.type];
  const previewUrl = item.metadata?.preview_url as string | undefined;
  const title = item.title || item.source_domain || 'Untitled capture';

  const confirmAction = async () => {
    if (!confirmation) return;
    setBusy(true);
    try {
      if (confirmation === 'favorite') await toggleFavorite(item.id);
      if (confirmation === 'archive') await toggleArchive(item.id);
      setConfirmation(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className={`item-card ${compact ? 'compact' : ''}`} style={{ animationDelay: `${index * 30}ms` }}>
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
          <Link to={`/items/${item.id}`}>{title}</Link>
        </h2>
        {item.type === 'text' ? (
          <blockquote>{item.raw_text}</blockquote>
        ) : (
          <p>{item.summary || item.description || item.url}</p>
        )}

        {item.search_match ? (
          <div className="search-explanation" aria-label="Why this result matched">
            <span>Matched by {item.search_match.reasons.join(', ')}</span>
            {item.search_match.snippet ? <p>{item.search_match.snippet}</p> : null}
          </div>
        ) : null}

        <div className="item-tags" aria-label="Tags">
          {item.tags.slice(0, 3).map((tag) => (
            <button key={tag.id} type="button" onClick={() => onTagClick?.(tag.name)}>
              #{tag.name}
            </button>
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
              onClick={() => setConfirmation('favorite')}
              title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
              aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            >
              <Star size={17} fill={item.is_favorite ? 'currentColor' : 'none'} />
            </button>
            <button
              type="button"
              onClick={() => setConfirmation('archive')}
              title={item.is_archived ? 'Restore' : 'Archive'}
              aria-label={item.is_archived ? 'Restore' : 'Archive'}
            >
              {item.is_archived ? <RotateCcw size={17} /> : <Archive size={17} />}
            </button>
            <Link className="show-details-button" to={`/items/${item.id}`} title={`Show details for ${title}`}>
              <Eye size={16} />
              <span>Details</span>
            </Link>
          </span>
        </footer>
      </div>
      {confirmation && (
        <ConfirmDialog
          title={confirmation === 'favorite'
            ? item.is_favorite ? 'Remove favorite?' : 'Add favorite?'
            : item.is_archived ? 'Restore item?' : 'Archive item?'}
          description={confirmation === 'favorite'
            ? `${title} will ${item.is_favorite ? 'leave' : 'appear in'} Favorites.`
            : `${title} will be ${item.is_archived ? 'restored to the library' : 'moved to Archive'}.`}
          confirmLabel={confirmation === 'favorite'
            ? item.is_favorite ? 'Remove favorite' : 'Add favorite'
            : item.is_archived ? 'Restore' : 'Archive'}
          busy={busy}
          onCancel={() => setConfirmation(null)}
          onConfirm={confirmAction}
        />
      )}
    </article>
  );
}
