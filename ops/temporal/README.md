# Temporal Analysis Operations

Memoryhive analysis uses the `memoryhive-analysis` task queue and a versioned
worker build ID. New workflow behavior must be introduced with Temporal patch
markers and retained until all histories created before the patch have expired.

Before enabling custom visibility fields, register them once:

```bash
cd cml-memoryhive-backend
uv run python -m app.temporal_pipeline.setup
```

Then set `TEMPORAL_CUSTOM_SEARCH_ATTRIBUTES_ENABLED=true`. Temporal UI will show
item type, a one-way tenant key, analysis version, provider, model, current stage,
and outcome. Raw user IDs and captured content are intentionally excluded.

Namespace workflow-history retention must be configured to the value in
`TEMPORAL_HISTORY_RETENTION_DAYS` (30 days by default) using the platform's
namespace administration process. Keep the corresponding worker patch code for
at least that retention window after the last old worker is removed.

Production must set `TEMPORAL_PAYLOAD_ENCRYPTION_REQUIRED=true` and provide a
Temporal `PayloadCodec` through the client data converter. The worker fails
closed when encryption is required but no codec is installed. Workflow inputs
contain only item/job identifiers, version, non-sensitive item type, and a hashed
tenant key; extracted personal content is checkpointed in the application
database by activities and is not returned into workflow history.

The `BackfillAnalysisWorkflow` accepts a bounded tuple of existing dispatch
requests. It exposes `pause`, `resume`, and `cancel` signals plus a `progress`
query, and starts child analysis workflows at the configured per-minute rate.

## Metrics

The observability configuration scrapes six bounded endpoints:

- API/application metrics at `cml-memoryhive-backend:8000/metrics`;
- database worker metrics at `cml-memoryhive-worker:9101/metrics`;
- Temporal Python SDK/Core metrics at
  `cml-memoryhive-temporal-worker:9102/metrics`;
- scheduler metrics at `cml-memoryhive-temporal-scheduler:9103/metrics`;
- Temporal activity/application metrics at
  `cml-memoryhive-temporal-worker:9104/metrics`;
- self-hosted Temporal Server metrics at `temporal:8000/metrics`.

Use `time() - memoryhive_worker_last_heartbeat_unixtime` to distinguish a
healthy idle loop from a stopped or wedged process. Queue depth, oldest age,
schedule-to-start, stuck analyses, stage outcomes, provider latency/errors,
fallbacks, tokens, cost, and circuit state use only bounded backend, component,
stage, outcome, provider, task, and operator-configured model-alias labels. Item,
user, workflow, request, and correlation IDs are log-only and never metric labels.

For Temporal Cloud, replace the self-hosted `temporal-server` scrape target with
the account metrics integration; keep the application and Python SDK scrape jobs.
