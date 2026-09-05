#!/usr/bin/env sh
set -eu

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ENV_FILE=${ENV_FILE:-.env.production}
BACKUP_ROOT=${BACKUP_ROOT:-backups}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_ROOT/$STAMP"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$DEST/minio"
DEST=$(cd "$DEST" && pwd)
compose exec -T db sh -c 'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format custom' > "$DEST/postgres.dump"

MINIO_CONTAINER=$(compose ps -q minio)
NETWORK=$(docker inspect "$MINIO_CONTAINER" --format '{{range $name, $config := .NetworkSettings.Networks}}{{$name}}{{end}}')
docker run --rm --network "$NETWORK" \
  --env-file "$ENV_FILE" \
  -v "$DEST:/backup" --entrypoint /bin/sh minio/mc \
  -c 'mc alias set source http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && if mc stat "source/$MINIO_BUCKET" >/dev/null 2>&1; then mc mirror --overwrite "source/$MINIO_BUCKET" /backup/minio; fi'

(cd "$DEST" && find . -type f ! -name SHA256SUMS -print | LC_ALL=C sort | while IFS= read -r file; do shasum -a 256 "$file"; done > SHA256SUMS)
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+${BACKUP_RETENTION_DAYS:-14}" -exec rm -rf {} +
printf '%s\n' "$DEST"
