#!/usr/bin/env sh
set -eu

BACKUP_DIR=${1:?Usage: ops/verify-backup.sh BACKUP_DIR}
COMPOSE_FILE=${COMPOSE_FILE:-cml-memoryhive-build/runtime/docker-compose.production.yml}
ENV_FILE=${ENV_FILE:-.env.production}
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
BACKUP_DIR=$(cd "$BACKUP_DIR" && pwd)
VERIFY_DB="memoryhive_verify_$(date +%s)"

(cd "$BACKUP_DIR" && shasum -a 256 -c SHA256SUMS)
compose exec -T db sh -c 'createdb --username "$POSTGRES_USER" "$1"' sh "$VERIFY_DB"
cleanup() { compose exec -T db sh -c 'dropdb --if-exists --username "$POSTGRES_USER" "$1"' sh "$VERIFY_DB" >/dev/null; }
trap cleanup EXIT INT TERM
compose exec -T db sh -c 'pg_restore --username "$POSTGRES_USER" --dbname "$1" --no-owner' sh "$VERIFY_DB" < "$BACKUP_DIR/postgres.dump"
compose exec -T db sh -c 'psql --username "$POSTGRES_USER" --dbname "$1" --tuples-only --command "SELECT count(*) FROM alembic_version;"' sh "$VERIFY_DB" | grep -Eq '[[:space:]]*1'
test -d "$BACKUP_DIR/minio"
printf 'Backup verified: %s\n' "$BACKUP_DIR"
