// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AdminAnalysisOperations, AdminAnalysisRunSummary } from '../types/api';
import AnalysisOperationsPanel from './AnalysisOperationsPanel';

afterEach(cleanup);

const run: AdminAnalysisRunSummary = {
  item_id: 'item-1',
  item_reference: 'link:item-1',
  job_id: 'job-1',
  workflow_id: 'analysis-item-1-v1',
  correlation_id: 'correlation-1',
  analysis_version: 1,
  backend: 'temporal',
  stage: 'enrich',
  provider: 'openrouter',
  model_alias: 'approved-model',
  status: 'completed',
  analysis_status: 'analyzed',
  enrichment_mode: 'ai',
  attempts: 1,
  max_attempts: 3,
  created_at: '2026-09-12T12:00:00Z',
  updated_at: '2026-09-12T12:00:01Z',
  completed_at: '2026-09-12T12:00:01Z',
  error_code: null,
};

const healthy: AdminAnalysisOperations = {
  queue_depth: 0,
  oldest_pending_age_seconds: null,
  status_counts: { completed: 1 },
  stage_counts: { persist: 1 },
  throughput_24h: 1,
  success_rate_24h: 1,
  degraded_rate_24h: 0,
  temporal_enabled: true,
  temporal_ui_url: 'http://localhost:8088',
  providers: [],
  recent_errors: [],
  recent_runs: [run],
};

const callbacks = { onRetry: vi.fn(), onCancel: vi.fn(), onReanalyze: vi.fn() };

describe('AnalysisOperationsPanel', () => {
  it('renders an empty state', () => {
    render(<AnalysisOperationsPanel {...callbacks} operations={{ ...healthy, recent_runs: [], throughput_24h: 0 }} providerHealth={[]} />);
    expect(screen.getByText('No analysis runs yet.')).toBeTruthy();
  });

  it('renders healthy state and Temporal correlation', () => {
    render(<AnalysisOperationsPanel {...callbacks} operations={healthy} providerHealth={[{
      provider: 'openrouter', available: true, latency_ms: 42, message: null, capabilities: ['enrichment'],
    }]} />);
    expect(screen.getByText('Healthy')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Temporal UI/ }).getAttribute('href')).toBe('http://localhost:8088');
    expect(screen.getByText('analysis-item-1-v1')).toBeTruthy();
  });

  it('renders degraded state', () => {
    render(<AnalysisOperationsPanel {...callbacks} operations={{ ...healthy, degraded_rate_24h: 0.25 }} providerHealth={[]} />);
    expect(screen.getByText('Degraded')).toBeTruthy();
    expect(screen.getByText('100% / 25%')).toBeTruthy();
  });

  it('renders failed state with only a sanitized error code', () => {
    render(<AnalysisOperationsPanel {...callbacks} operations={{
      ...healthy,
      status_counts: { failed: 1 },
      recent_runs: [{ ...run, status: 'failed', analysis_status: 'failed', error_code: 'provider_unavailable' }],
      recent_errors: [{ item_reference: 'link:item-1', job_id: 'job-1', workflow_id: run.workflow_id, correlation_id: run.correlation_id, stage: 'enrich', provider: 'openrouter', code: 'provider_unavailable', occurred_at: run.updated_at }],
    }} providerHealth={[]} />);
    expect(screen.getByText('Failures detected')).toBeTruthy();
    expect(screen.getAllByText('provider_unavailable').length).toBeGreaterThan(0);
  });

  it('renders unavailable state without hiding the rest of admin', () => {
    render(<AnalysisOperationsPanel {...callbacks} operations={null} providerHealth={[]} unavailableMessage="Operations service is offline." />);
    expect(screen.getByText('Unavailable')).toBeTruthy();
    expect(screen.getByText('Operations service is offline.')).toBeTruthy();
  });
});
