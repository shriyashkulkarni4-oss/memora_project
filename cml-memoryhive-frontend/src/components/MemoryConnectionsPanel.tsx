import { AlertTriangle, Link2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { itemsApi } from '../services/api';
import type { DuplicateMatch, MemoryMatch } from '../types/api';

export default function MemoryConnectionsPanel({ itemId }: { itemId: string }) {
  const [related, setRelated] = useState<MemoryMatch[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateMatch[]>([]);

  useEffect(() => {
    let active = true;
    void Promise.all([itemsApi.related(itemId), itemsApi.duplicates(itemId)])
      .then(([nextRelated, nextDuplicates]) => {
        if (active) {
          setRelated(nextRelated);
          setDuplicates(nextDuplicates);
        }
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, [itemId]);

  if (!related.length && !duplicates.length) return null;
  return (
    <section className="content-section memory-connections" aria-label="Memory connections">
      <span className="section-label">Memory connections</span>
      {duplicates.length ? (
        <div className="duplicate-notice">
          <AlertTriangle size={16} />
          <div>
            <strong>Possible duplicate{duplicates.length > 1 ? 's' : ''}</strong>
            {duplicates.map((match) => (
              <p key={match.item.id}>
                <Link to={`/items/${match.item.id}`}>{match.item.title || 'Untitled capture'}</Link>
                {' — '}{match.reasons.join(', ')}. Nothing is merged automatically.
              </p>
            ))}
          </div>
        </div>
      ) : null}
      {related.length ? (
        <div className="related-memory-list">
          {related.map((match) => (
            <Link key={match.item.id} to={`/items/${match.item.id}`}>
              <Link2 size={15} />
              <span><strong>{match.item.title || match.item.source_domain || 'Untitled capture'}</strong><small>{match.reasons.join(' · ')}</small></span>
            </Link>
          ))}
        </div>
      ) : null}
    </section>
  );
}
