import { Check, RotateCcw, Sparkles, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { itemsApi } from '../services/api';
import type { AISuggestion, AISuggestionDecision, AISuggestionOverview, Item } from '../types/api';

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';

function demoOverview(item: Item): AISuggestionOverview | null {
  const enrichment = item.metadata?.enrichment;
  if (!enrichment || typeof enrichment !== 'object') return null;
  const value = enrichment as Record<string, unknown>;
  const tags = Array.isArray(value.suggested_tags) ? value.suggested_tags.filter((tag): tag is string => typeof tag === 'string') : [];
  const classification = typeof value.classification === 'string' ? value.classification : null;
  const confidence = typeof value.confidence === 'number' ? value.confidence : null;
  return {
    item_id: item.id,
    analysis_version: item.analysis_version,
    item_revision: item.revision,
    topics: Array.isArray(value.topics) ? value.topics.filter((topic): topic is string => typeof topic === 'string') : [],
    classification,
    suggestions: [
      ...tags.map((tag): AISuggestion => ({ suggestion_type: 'tag', value: tag, confidence, status: 'pending', can_undo: false })),
      ...(classification ? [{ suggestion_type: 'classification' as const, value: classification, confidence, status: 'pending' as const, can_undo: false }] : []),
    ],
  };
}

interface Props {
  item: Item;
  onChanged: () => Promise<void>;
}

export default function AISuggestionsPanel({ item, onChanged }: Props) {
  const [overview, setOverview] = useState<AISuggestionOverview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!['analyzed', 'degraded'].includes(item.analysis_status)) return;
    let active = true;
    void (demoMode ? Promise.resolve(demoOverview(item)) : itemsApi.suggestions(item.id))
      .then((value) => { if (active) setOverview(value); })
      .catch(() => { if (active) setOverview(null); });
    return () => { active = false; };
  }, [item]);

  const pending = useMemo(() => overview?.suggestions.filter((entry) => entry.status === 'pending') || [], [overview]);

  const decide = async (decisions: AISuggestionDecision[]) => {
    if (!overview) return;
    setBusy(true);
    setError('');
    try {
      if (demoMode) {
        const keys = new Map(decisions.map((entry) => [`${entry.suggestion_type}:${entry.value}`, entry.action]));
        setOverview({
          ...overview,
          suggestions: overview.suggestions.map((entry) => {
            const action = keys.get(`${entry.suggestion_type}:${entry.value}`);
            if (!action) return entry;
            return { ...entry, status: action === 'accept' ? 'accepted' : action === 'undo' ? 'pending' : action === 'never' ? 'never' : 'rejected', can_undo: action === 'accept' };
          }),
        });
      } else {
        setOverview(await itemsApi.decideSuggestions(item.id, {
          client_id: crypto.randomUUID(),
          analysis_version: overview.analysis_version,
          expected_revision: overview.item_revision,
          decisions,
        }));
        await onChanged();
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to save suggestion decision');
    } finally {
      setBusy(false);
    }
  };

  if (!overview || (!overview.suggestions.length && !overview.topics.length)) return null;
  return (
    <section className="content-section ai-suggestions" aria-labelledby="ai-suggestions-title">
      <header>
        <span className="section-label" id="ai-suggestions-title"><Sparkles size={14} /> AI suggestions</span>
        {pending.length > 1 ? (
          <button className="button secondary" type="button" disabled={busy} onClick={() => void decide(pending.map(({ suggestion_type, value }) => ({ suggestion_type, value, action: 'accept' })))}>
            Accept all
          </button>
        ) : null}
      </header>
      {overview.classification ? <p><strong>Classification:</strong> {overview.classification}</p> : null}
      {overview.topics.length ? <p><strong>Topics:</strong> {overview.topics.join(' · ')}</p> : null}
      <div className="suggestion-list">
        {overview.suggestions.map((suggestion) => (
          <div key={`${suggestion.suggestion_type}:${suggestion.value}`} className={`suggestion ${suggestion.status}`}>
            <span>{suggestion.suggestion_type === 'tag' ? '#' : ''}{suggestion.value}</span>
            <small>{suggestion.confidence === null ? '' : `${Math.round(suggestion.confidence * 100)}%`} {suggestion.status}</small>
            {suggestion.status === 'pending' ? <>
              <button type="button" disabled={busy} aria-label={`Accept ${suggestion.value}`} onClick={() => void decide([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: 'accept' }])}><Check size={14} /></button>
              <button type="button" disabled={busy} aria-label={`Reject ${suggestion.value}`} onClick={() => void decide([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: 'reject' }])}><X size={14} /></button>
              {suggestion.suggestion_type === 'tag' ? <button type="button" disabled={busy} onClick={() => void decide([{ suggestion_type: 'tag', value: suggestion.value, action: 'never' }])}>Never</button> : null}
            </> : suggestion.can_undo ? (
              <button type="button" disabled={busy} onClick={() => void decide([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: 'undo' }])}><RotateCcw size={14} /> Undo</button>
            ) : null}
          </div>
        ))}
      </div>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <small>Suggestions never replace your tags or category without your action.</small>
    </section>
  );
}
