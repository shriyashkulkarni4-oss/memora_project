import { Pin, RotateCcw, Sparkles, ThumbsUp, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { itemsApi } from '../services/api';
import type { MemoryFeedback, MemoryMatch } from '../types/api';

export default function ResurfacingPanel() {
  const [matches, setMatches] = useState<MemoryMatch[]>([]);
  const [last, setLast] = useState<MemoryFeedback | null>(null);

  useEffect(() => {
    if (import.meta.env.VITE_DEMO_MODE === 'true') return;
    void itemsApi.resurfacing().then((page) => setMatches(page.items)).catch(() => undefined);
  }, []);

  const decide = async (match: MemoryMatch, action: 'dismiss' | 'pin' | 'useful') => {
    const event = await itemsApi.resurfacingFeedback(match.item.id, {
      action,
      client_id: crypto.randomUUID(),
    });
    setLast(event);
    if (action === 'dismiss') setMatches((values) => values.filter((value) => value.item.id !== match.item.id));
  };

  const undo = async () => {
    if (!last) return;
    await itemsApi.resurfacingFeedback(last.item_id, {
      action: 'undo',
      client_id: crypto.randomUUID(),
      reverses_id: last.id,
    });
    setLast(null);
  };

  if (!matches.length && !last) return null;
  return (
    <section className="resurfacing-panel" aria-label="Rediscover memories">
      <header><div><Sparkles size={17} /><strong>Rediscover</strong></div>{last ? <button type="button" onClick={() => void undo()}><RotateCcw size={14} /> Undo feedback</button> : null}</header>
      <div>
        {matches.slice(0, 4).map((match) => (
          <article key={match.item.id}>
            <Link to={`/items/${match.item.id}`}>{match.item.title || match.item.source_domain || 'Untitled capture'}</Link>
            <p>{match.reasons.join(' · ')}</p>
            <span>
              <button type="button" onClick={() => void decide(match, 'useful')} aria-label="Mark resurfaced memory useful"><ThumbsUp size={14} /></button>
              <button type="button" onClick={() => void decide(match, 'pin')} aria-label="Pin resurfaced memory"><Pin size={14} /></button>
              <button type="button" onClick={() => void decide(match, 'dismiss')} aria-label="Dismiss resurfaced memory"><X size={14} /></button>
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}
