# Operations Runbook

Last updated: 2026-09-06

## Deploy

1. Provision a Linux host with Docker Engine, Compose v2, DNS for `APP_DOMAIN`,
   and encrypted persistent storage.
2. Copy `.env.production.example` to `.env.production`, set unique values, and
   restrict it with `chmod 600 .env.production`. Prefer injecting these values
   from the hosting platform's secret manager.
3. Set immutable `BACKEND_IMAGE` and `FRONTEND_IMAGE` tags from a `v*` release.
4. Validate and start the stack:

```bash
docker compose --env-file .env.production -f cml-memoryhive-build/runtime/docker-compose.production.yml config --quiet
docker compose --env-file .env.production -f cml-memoryhive-build/runtime/docker-compose.production.yml pull
docker compose --env-file .env.production -f cml-memoryhive-build/runtime/docker-compose.production.yml up -d
BASE_URL=https://www.memoryhive.in ops/smoke.sh
```

Caddy terminates TLS and renews certificates. The API migration runs before its
web workers start. Enable local-only Prometheus with `--profile observability`.
Forward Prometheus alerts to the organization's existing alert manager.

## Routine checks

- `/health/live`: process liveness.
- `/health/ready`: database readiness.
- `/metrics`: internal Prometheus scrape endpoint.
- `docker compose ... ps`: container health.
- `docker compose ... logs --since 15m cml-memoryhive-backend cml-memoryhive-worker`: structured request and
  processing logs.

Investigate sustained 5xx errors, p95 latency above one second, a failed worker,
or a growing processing backlog. Request IDs correlate client reports to logs.

## Processing operations

Admins can inspect recent background jobs from the web Admin page or
`GET /api/v1/admin/processing/jobs`. Filter with `?status=failed` to triage
exhausted link metadata and screenshot OCR jobs. Retry a failed job with
`POST /api/v1/admin/processing/jobs/{job_id}/retry`; this creates a new pending
job and keeps the failed job as audit history. Do not retry jobs repeatedly
until the underlying worker dependency, such as outbound fetch access or
Tesseract OCR, has been fixed.

Temporal-backed analysis is optional. Enable it with `TEMPORAL_ENABLED=true` and
run the `temporal` Compose profile or point `TEMPORAL_ADDRESS` at a private
Temporal cluster. Check `analysis_status`, `pending_analysis`, and
`failed_analysis` before disabling the legacy worker path. Keep Temporal UI and
frontend ports internal to operators; do not expose them publicly.

## Backup and recovery

Run daily and copy the resulting directory to encrypted off-host storage:

```bash
BACKUP_ROOT=/srv/memoryhive-backups ops/backup.sh
ops/verify-backup.sh /srv/memoryhive-backups/20260905T120000Z
```

The backup contains a PostgreSQL custom dump, an object-level MinIO mirror, and
SHA-256 checksums. Verification restores the database into a temporary database
without touching production. Perform a full recovery exercise quarterly in an
isolated environment.

Admins can view backup status in the web Admin page through `/api/v1/admin/backup`.
The Admin "Run backup" button remains disabled until `ADMIN_BACKUP_COMMAND` is
configured. Use that setting only in deployments where the backend process can
execute the operations command and access the intended `BACKUP_ROOT`; leave it
blank when backups are owned by an external scheduler.

Full restore is destructive and briefly stops the API and worker:

```bash
CONFIRM_RESTORE=cml-memoryhive ops/restore.sh /srv/memoryhive-backups/20260905T120000Z
BASE_URL=https://www.memoryhive.in ops/smoke.sh
```

## Incident and rollback

1. Stop writes by placing the ingress in maintenance mode or stopping Caddy.
2. Capture logs, container state, release tag, and a fresh backup when safe.
3. Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to the last verified immutable tags.
4. Run `docker compose ... up -d`. Alembic migrations are forward-only during a
   normal rollback; restore the pre-release backup if the old application cannot
   read the migrated schema.
5. Run `ops/smoke.sh`, verify processing, then restore traffic.

Never run `docker compose down --volumes` against a production project.
