import { Activity, AlertTriangle, ExternalLink, RefreshCw, StopCircle } from 'lucide-react';
import type { AdminAIProviderHealth, AdminAnalysisOperations, AdminAnalysisRunSummary } from '../types/api';

interface Props {
  operations: AdminAnalysisOperations | null;
  providerHealth: AdminAIProviderHealth[];
  unavailableMessage?: string;
  busy?: boolean;
  onRetry: (run: AdminAnalysisRunSummary) => void;
  onCancel: (run: AdminAnalysisRunSummary) => void;
  onReanalyze: (run: AdminAnalysisRunSummary) => void;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function age(value: number | null) {
  if (value === null) return 'None';
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

export default function AnalysisOperationsPanel({
  operations,
  providerHealth,
  unavailableMessage,
  busy = false,
  onRetry,
  onCancel,
  onReanalyze,
}: Props) {
  if (!operations) {
    return (
      <section className="admin-panel" aria-labelledby="analysis-operations-heading">
        <div className="section-heading">
          <div><Activity size={19} /><h2 id="analysis-operations-heading">Analysis Operations</h2></div>
          <span className="status-badge disabled">Unavailable</span>
        </div>
        <div className="admin-empty" role="status">{unavailableMessage || 'Analysis operations data is unavailable.'}</div>
      </section>
    );
  }

  const degraded = operations.degraded_rate_24h > 0;
  const failed = (operations.status_counts.failed || 0) > 0;
  return (
    <section className="admin-panel" aria-labelledby="analysis-operations-heading">
      <div className="section-heading">
        <div><Activity size={19} /><h2 id="analysis-operations-heading">Analysis Operations</h2></div>
        <div className="admin-operations-links">
          <span className={`status-badge ${failed ? 'disabled' : degraded ? 'warning' : 'active'}`}>
            {failed ? 'Failures detected' : degraded ? 'Degraded' : 'Healthy'}
          </span>
          {operations.temporal_ui_url ? (
            <a className="button secondary" href={operations.temporal_ui_url} target="_blank" rel="noreferrer">
              Temporal UI <ExternalLink size={14} />
            </a>
          ) : null}
        </div>
      </div>

      <div className="admin-metrics admin-analysis-metrics" aria-label="Analysis metrics">
        <div><span>Queue depth</span><strong>{operations.queue_depth}</strong></div>
        <div><span>Oldest queued</span><strong>{age(operations.oldest_pending_age_seconds)}</strong></div>
        <div><span>24h throughput</span><strong>{operations.throughput_24h}</strong></div>
        <div><span>Success / degraded</span><strong>{percent(operations.success_rate_24h)} / {percent(operations.degraded_rate_24h)}</strong></div>
      </div>

      <div className="admin-provider-health" aria-label="AI provider connectivity">
        {providerHealth.length ? providerHealth.map((provider) => (
          <div key={provider.provider}>
            <span className={`status-badge ${provider.available ? 'active' : 'disabled'}`}>
              {provider.available ? 'Available' : 'Unavailable'}
            </span>
            <strong>{provider.provider}</strong>
            <small>{provider.latency_ms === null ? 'No latency sample' : `${provider.latency_ms} ms`}</small>
          </div>
        )) : <div className="admin-empty">No configured AI providers.</div>}
      </div>

      {operations.recent_errors.length ? (
        <div className="admin-recent-errors" aria-label="Recent analysis errors">
          {operations.recent_errors.map((record) => (
            <div key={`${record.job_id}-${record.occurred_at}`}>
              <AlertTriangle size={14} />
              <strong>{record.code}</strong>
              <span>{record.item_reference} · {record.stage} · {record.provider || 'no provider'}</span>
            </div>
          ))}
        </div>
      ) : null}

      {operations.recent_runs.length ? (
        <div className="admin-processing-table" aria-label="Recent analysis runs">
          {operations.recent_runs.map((run) => (
            <div className="admin-processing-row admin-analysis-row" key={run.job_id}>
              <div>
                <strong>{run.item_reference}</strong>
                <small>v{run.analysis_version ?? '—'} · {run.enrichment_mode.replace('_', ' ')}</small>
              </div>
              <span>{run.backend} · {run.stage}</span>
              <span className={`job-status-badge ${run.status}`}>{run.status}</span>
              <span>{run.provider || 'none'} / {run.model_alias || 'default'}</span>
              <small title={run.correlation_id}>{run.workflow_id || run.correlation_id}</small>
              <small>{run.error_code || 'No error'}</small>
              <div className="admin-processing-actions">
                <button className="button secondary" type="button" disabled={run.status !== 'failed' || busy} onClick={() => onRetry(run)}>
                  <RefreshCw size={14} /> Retry
                </button>
                <button className="button secondary" type="button" disabled={!['pending', 'scheduled', 'processing'].includes(run.status) || busy} onClick={() => onCancel(run)}>
                  <StopCircle size={14} /> Cancel
                </button>
                <button className="button secondary" type="button" disabled={['pending', 'scheduled', 'processing'].includes(run.status) || busy} onClick={() => onReanalyze(run)}>
                  Reanalyze
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : <div className="admin-empty">No analysis runs yet.</div>}
    </section>
  );
}
