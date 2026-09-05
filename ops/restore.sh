#!/usr/bin/env sh
set -eu

BACKUP_DIR=${1:?Usage: CONFIRM_RESTORE=memoryhive ops/restore.sh BACKUP_DIR}
test "${CONFIRM_RESTORE:-}" = "memoryhive" || { echo "Set CONFIRM_RESTORE=memoryhive to continue" >&2; exit 2; }
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ENV_FILE=${ENV_FILE:-.env.production}
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
BACKUP_DIR=$(cd "$BACKUP_DIR" && pwd)

(cd "$BACKUP_DIR" && shasum -a 256 -c SHA256SUMS)
compose stop backend worker
compose exec -T db sh -c 'dropdb --if-exists --force --username "$POSTGRES_USER" "$POSTGRES_DB"'
compose exec -T db sh -c 'createdb --username "$POSTGRES_USER" "$POSTGRES_DB"'
compose exec -T db sh -c 'pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-owner' < "$BACKUP_DIR/postgres.dump"

MINIO_CONTAINER=$(compose ps -q minio)
NETWORK=$(docker inspect "$MINIO_CONTAINER" --format '{{range $name, $config := .NetworkSettings.Networks}}{{$name}}{{end}}')
docker run --rm --network "$NETWORK" \
  --env-file "$ENV_FILE" \
  -v "$BACKUP_DIR:/backup:ro" --entrypoint /bin/sh minio/mc \
  -c 'mc alias set target http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc mb --ignore-existing "target/$MINIO_BUCKET" >/dev/null && mc mirror --overwrite --remove /backup/minio "target/$MINIO_BUCKET"'
compose up -d backend worker
printf 'Restore completed from %s\n' "$BACKUP_DIR"
