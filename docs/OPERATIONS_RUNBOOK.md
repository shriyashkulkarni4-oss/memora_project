# Operations Runbook

Last updated: 2026-09-05

## Deploy

1. Provision a Linux host with Docker Engine, Compose v2, DNS for `APP_DOMAIN`,
   and encrypted persistent storage.
2. Copy `.env.production.example` to `.env.production`, set unique values, and
   restrict it with `chmod 600 .env.production`. Prefer injecting these values
   from the hosting platform's secret manager.
3. Set immutable `BACKEND_IMAGE` and `FRONTEND_IMAGE` tags from a `v*` release.
4. Validate and start the stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
BASE_URL=https://memoryhive.example.com ops/smoke.sh
```

Caddy terminates TLS and renews certificates. The API migration runs before its
web workers start. Enable local-only Prometheus with `--profile observability`.
Forward Prometheus alerts to the organization's existing alert manager.

## Routine checks

- `/health/live`: process liveness.
- `/health/ready`: database readiness.
- `/metrics`: internal Prometheus scrape endpoint.
- `docker compose ... ps`: container health.
- `docker compose ... logs --since 15m backend worker`: structured request and
  processing logs.

Investigate sustained 5xx errors, p95 latency above one second, a failed worker,
or a growing processing backlog. Request IDs correlate client reports to logs.

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

Full restore is destructive and briefly stops the API and worker:

```bash
CONFIRM_RESTORE=memoryhive ops/restore.sh /srv/memoryhive-backups/20260905T120000Z
BASE_URL=https://memoryhive.example.com ops/smoke.sh
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
