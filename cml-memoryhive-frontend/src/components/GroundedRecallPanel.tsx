import { BookOpen, Send, Sparkles } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { itemsApi } from '../services/api';
import type { GroundedRecall } from '../types/api';

export default function GroundedRecallPanel() {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<GroundedRecall | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (import.meta.env.VITE_GROUNDED_RECALL_ENABLED !== 'true') return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setLoading(true);
    setError('');
    try {
      setResult(await itemsApi.recall(question.trim()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Grounded recall is unavailable');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="recall-panel" aria-label="Ask your saved memories">
      <header><Sparkles size={17} /><div><strong>Ask your memories</strong><p>Answers use only your saved items.</p></div></header>
      <form onSubmit={(event) => void submit(event)}>
        <label><span className="sr-only">Question about saved memories</span><input value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={500} placeholder="What have I saved about…?" /></label>
        <button type="submit" disabled={loading || question.trim().length < 3} aria-label="Ask memories"><Send size={15} /></button>
      </form>
      {error ? <p className="form-error">{error}</p> : null}
      {result ? (
        <div className="recall-answer">
          <p>{result.answer}</p>
          {result.citations.length ? <ol>{result.citations.map((citation) => (
            <li key={citation.citation_id}><BookOpen size={13} /><Link to={`/items/${citation.item_id}`}>[{citation.citation_id}] {citation.title || 'Saved item'}</Link><span>{citation.passage}</span></li>
          ))}</ol> : null}
          <small>No web search was used{result.model ? ` · ${result.provider}/${result.model}` : ''}.</small>
        </div>
      ) : null}
    </section>
  );
}
