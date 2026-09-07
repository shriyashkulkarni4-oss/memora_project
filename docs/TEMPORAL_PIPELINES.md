# Temporal Processing Pipelines

Memoryhive now has an optional Temporal pipeline for durable offline analysis of
captured items. The existing database-backed worker remains the default path;
Temporal is enabled only when `TEMPORAL_ENABLED=true` and the Temporal services
or an external Temporal cluster are available.

## What Runs in Temporal

`AnalyzeItemWorkflow` runs on `TEMPORAL_TASK_QUEUE` and calls
`analyze_item_activity`. The activity reuses the existing content processor:

- Links: fetch readable public content, extract metadata/text, summarize.
- Screenshots: read the private asset, run OCR, detect language, summarize.
- Text captures: normalize raw text, detect language, summarize.

Workflow IDs use `memoryhive-analysis-{item_id}-v{analysis_version}`. This keeps
retries idempotent and prevents stale workflows from overwriting newer edits.

## Analysis State

Items now track durable analysis metadata:

- `analysis_status`: `pending`, `analyzing`, `analyzed`, `failed`, `skipped`, or `not_analyzed`.
- `analysis_version`: increments when item content changes.
- `analysis_requested_at`, `analysis_started_at`, `analysis_completed_at`.
- `analysis_error`: last failed activity error, truncated server-side.

The API includes these fields in item responses and item stats include
`pending_analysis` and `failed_analysis`.

## Local Development

Start the Temporal profile:

```bash
cml-memoryhive-build/runtime/manage_services_docker.sh start --profile temporal
```

Temporal service listens on `localhost:7233`; Temporal UI listens on
`localhost:${TEMPORAL_UI_PORT:-8088}`. The profile adds:

- `temporal-db`
- `temporal`
- `temporal-ui`
- `temporal-worker`
- `temporal-scheduler`

Run the scheduler once for debugging:

```bash
cd cml-memoryhive-backend
TEMPORAL_ENABLED=true TEMPORAL_ADDRESS=localhost:7233 ./.venv/bin/python -m app.temporal_pipeline.scheduler --once
```

## Production Notes

Production Compose does not start a Temporal server. Point `TEMPORAL_ADDRESS` at
Temporal Cloud or an internally operated Temporal cluster, then enable the
`temporal` profile for `temporal-worker` and `temporal-scheduler`. Keep Temporal
network access private and treat its UI as an operator-only surface.
