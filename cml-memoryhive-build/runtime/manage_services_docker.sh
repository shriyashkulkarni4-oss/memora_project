#!/usr/bin/env sh
set -eu

RUNTIME_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_ROOT=$(CDPATH= cd -- "$RUNTIME_ROOT/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$BUILD_ROOT/.." && pwd)
COMMAND=${1:-help}
if [ "$#" -gt 0 ]; then shift; fi
PROFILE=${PROFILE:-full}
if [ "${1:-}" = "--profile" ]; then
  PROFILE=${2:?--profile requires infra, app-only, full, or temporal}
  shift 2
fi
case "$PROFILE" in infra|app-only|full|temporal) ;; *) echo "unknown profile: $PROFILE" >&2; exit 2 ;; esac

ENV_FILE=${ENV_FILE:-$REPO_ROOT/.env}
COMPOSE_FILE="$RUNTIME_ROOT/docker-compose.$PROFILE.yml"
BASE_URL=${BASE_URL:-http://localhost:${BACKEND_PORT:-8000}}

generate() { python3 "$BUILD_ROOT/scripts/generate_runtime.py"; }
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$REPO_ROOT/.env.example" "$ENV_FILE"
    printf 'Created %s from .env.example\n' "$ENV_FILE"
  fi
}

usage() {
  cat <<'EOF'
Usage: cml-memoryhive-build/runtime/manage_services_docker.sh COMMAND [--profile PROFILE] [args]

Commands:
  generate   Regenerate all Compose and health-registry files
  start      Check ports and start the selected profile
  stop       Stop without deleting volumes
  restart    Rebuild and restart the selected profile
  status     Show service status
  logs       Follow selected profile logs
  migrate    Run Alembic migrations
  rate-reset Clear local Redis rate-limit counters
  seed       Seed demo data through the public API
  smoke      Run the authenticated API smoke test
  validate   Validate Compose config and backend readiness when applicable
  clean      Delete containers and volumes; requires CONFIRM_CLEAN=cml-memoryhive
EOF
}

cd "$REPO_ROOT"
case "$COMMAND" in
  generate) generate ;;
  start)
    ensure_env; generate
    python3 "$BUILD_ROOT/scripts/check_ports.py" "$PROFILE"
    compose up --build --detach
    ;;
  stop) ensure_env; generate; compose down ;;
  restart)
    ensure_env; generate
    compose down --remove-orphans
    python3 "$BUILD_ROOT/scripts/check_ports.py" "$PROFILE"
    compose up --build --detach --remove-orphans
    ;;
  status) ensure_env; generate; compose ps ;;
  logs) ensure_env; generate; compose logs --follow ;;
  migrate) ensure_env; generate; compose run --rm migrate ;;
  rate-reset)
    ensure_env; generate
    compose exec -T redis redis-cli EVAL "for _,key in ipairs(redis.call('keys', ARGV[1])) do redis.call('del', key) end return 1" 0 'rate:*' >/dev/null
    ;;
  seed) python3 seed_data.py --base-url "$BASE_URL" "$@" ;;
  smoke) BASE_URL="$BASE_URL" "$REPO_ROOT/ops/smoke.sh" ;;
  validate)
    ensure_env; generate; compose config --quiet
    if [ "$PROFILE" != "infra" ]; then
      curl --fail --silent "$BASE_URL/health/ready" >/dev/null
    fi
    printf 'Profile %s is valid%s\n' "$PROFILE" "${PROFILE:+ and ready when applicable}"
    ;;
  clean)
    ensure_env; generate
    if [ "${CONFIRM_CLEAN:-}" != "cml-memoryhive" ]; then
      echo "Refusing to delete volumes. Re-run with CONFIRM_CLEAN=cml-memoryhive." >&2
      exit 2
    fi
    compose down --volumes --remove-orphans
    ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
