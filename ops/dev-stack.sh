#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMAND=${1:-help}
if [ "$#" -gt 0 ]; then shift; fi

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
ENV_FILE=${ENV_FILE:-.env}
BASE_URL=${BASE_URL:-http://localhost:${BACKEND_PORT:-8000}}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

compose_temporal() {
  TEMPORAL_ENABLED=true docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile temporal "$@"
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    cp .env.example "$ENV_FILE"
    printf 'Created %s from .env.example\n' "$ENV_FILE"
  fi
}

usage() {
  cat <<'EOF'
Usage: ops/dev-stack.sh COMMAND [args]

Commands:
  start       Create .env if needed and start the full Docker dev stack
  stop        Stop the Docker dev stack without deleting volumes
  restart     Rebuild and restart the Docker dev stack
  temporal    Start the dev stack with Temporal server, UI, scheduler, and worker
  status      Show Compose service status
  logs        Follow backend, worker, frontend, and Temporal app logs
  migrate     Run Alembic migrations with the one-shot migrate service
  rate-reset  Clear transient Redis rate-limit counters for repeatable local tests
  validate    Check Compose status plus backend readiness
  load        Seed demo data through the public API
  smoke       Run the authenticated API smoke test
  clean       Delete containers and volumes; requires CONFIRM_CLEAN=memoryhive

Examples:
  ops/dev-stack.sh start
  ops/dev-stack.sh load --persona engineer
  CONFIRM_CLEAN=memoryhive ops/dev-stack.sh clean
EOF
}

cd "$ROOT"

case "$COMMAND" in
  start)
    ensure_env
    compose up --build --detach
    ;;
  stop)
    ensure_env
    compose down
    ;;
  restart)
    ensure_env
    compose up --build --detach --remove-orphans
    ;;
  temporal)
    ensure_env
    compose_temporal up --build --detach --remove-orphans
    ;;
  status)
    ensure_env
    compose ps
    ;;
  logs)
    ensure_env
    compose --profile temporal logs --follow backend worker frontend temporal-worker temporal-scheduler
    ;;
  migrate)
    ensure_env
    compose run --rm migrate
    ;;
  rate-reset)
    ensure_env
    compose exec -T redis redis-cli EVAL "for _,key in ipairs(redis.call('keys', ARGV[1])) do redis.call('del', key) end return 1" 0 'rate:*' >/dev/null
    ;;
  validate)
    ensure_env
    compose ps
    curl --fail --silent "$BASE_URL/health/ready" >/dev/null
    printf 'Development stack is ready: %s\n' "$BASE_URL"
    ;;
  load)
    ensure_env
    python3 seed_data.py --base-url "$BASE_URL" "$@"
    ;;
  smoke)
    ensure_env
    BASE_URL="$BASE_URL" ops/smoke.sh
    ;;
  clean)
    ensure_env
    if [ "${CONFIRM_CLEAN:-}" != "memoryhive" ]; then
      printf 'Refusing to delete Docker volumes. Re-run with CONFIRM_CLEAN=memoryhive.\n' >&2
      exit 2
    fi
    compose down --volumes --remove-orphans
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
