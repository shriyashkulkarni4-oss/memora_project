# Memoryhive Observability Runbook

Owner routing: `platform` owns API, runtime, database, network, Prometheus,
Grafana, Alertmanager, and Temporal Server availability. `ai-platform` owns
dispatch, workers, workflow/activity execution, and provider connectivity.
`product-operations` owns budget changes and customer-impact communication.

Never paste captured content, raw prompts/responses, tokens, provider keys, user
IDs, or item IDs into alerts or shared incident channels. Correlate through the
bounded request/job/workflow correlation ID in restricted logs and Admin.

## API unavailable

Query `up{job="cml-memoryhive-api"}`. Check readiness, database/Redis/MinIO,
workload restarts, and the current release. Restore the dependency or roll back;
verify capture and search before resolving.

## Missing poller

Query `time() - memoryhive_worker_last_heartbeat_unixtime`. Compare the custom
worker target with Temporal SDK poll metrics. Check task queue/namespace/build ID,
database access, and process logs. Restart only after fixing the dependency; a
healthy idle worker must refresh its heartbeat.

## Temporal unavailable

Query `up{job="temporal-server"}` and inspect Temporal frontend and persistence
health. Confirm DNS/network policy and database capacity. Restore the cluster and
verify a synthetic workflow; do not switch execution backends for existing jobs.

## Backlog

Query `memoryhive_analysis_queue_pending` and enqueue/completion rates. Compare
oldest age, schedule-to-start, worker heartbeat, provider latency, and database
capacity. Scale only within provider concurrency and database limits.

## Oldest pending

Query `memoryhive_analysis_queue_oldest_age_seconds`. Identify the backend and use
Admin's safe job reference to inspect its stage. Recover stale claims or use the
guarded retry/backfill operation after the underlying issue is resolved.

## Stuck analysis

Query `memoryhive_analysis_stuck` and stage outcomes. Inspect the correlated
workflow history or database job lock. Cancel/retry idempotently; never mutate
Temporal history or database state by hand.

## Activity failures

Query `sum by (stage,outcome)
(rate(memoryhive_analysis_outcomes_total{backend="temporal"}[5m]))` plus Temporal
SDK failure/retry metrics. Fix the failing activity dependency or deploy backward-
compatible workflow/activity code.

## Degraded spike

Compare degraded outcomes with provider errors, budgets, circuits, and fallback
rate. Deterministic extraction remains usable. Restore the approved provider or
disable its route deliberately; verify privacy policy before rerouting.

## Provider auth

Group `memoryhive_ai_calls_total` by provider/model alias/outcome. Verify the
secret reference and provider account without printing secret values. Rotate the
credential and run the content-free health check.

## Provider rate limit

Compare call rate, retries, concurrency, and provider quota. Reduce concurrency,
request approved quota, or enable a reviewed fallback. Confirm backlog recovery.

## Provider circuit

Inspect recent normalized provider errors and health. Restore connectivity and
allow the configured reset/probe cycle to close the circuit; do not bypass it.

## Budget

Review database usage totals against daily/monthly request, token, cost, and
per-user quotas. Never add user IDs to metrics. Wait for reset or obtain product-
operations approval for a budget change; deterministic processing continues.

## Fallback spike

Compare primary errors/latency with fallback outcomes and cost. Repair or disable
the primary only after confirming the fallback's external-data and budget policy.

## API errors

Group request rate by bounded route/status and use correlation IDs in restricted
logs. Restore the failing dependency or roll back, then verify the affected flow.

## API latency

Compare route p95 with database, Redis, object storage, worker, and provider
latency. Remove the bottleneck or scale the constrained stateless service.

## Synthetic alert drills

Run `promtool test rules ops/tests/alerts.test.yml` when Prometheus tooling is
available. The checked fixtures exercise backlog and circuit alerts. In the local
observability profile, stopping a worker exercises missing-poller detection;
restore it immediately after Alertmanager receives the firing notification.
