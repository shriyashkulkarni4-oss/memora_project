#!/usr/bin/env sh
set -eu

BASE_URL=${BASE_URL:-http://localhost:8000}
CURL_RESOLVE=${CURL_RESOLVE:-}
EMAIL="release-smoke-$(date +%s)@example.com"
PASSWORD="Release-smoke-password-123"

request() {
  if [ -n "$CURL_RESOLVE" ]; then
    curl --resolve "$CURL_RESOLVE" "$@"
  else
    curl "$@"
  fi
}

request --fail --silent "$BASE_URL/health/ready" | grep -q '"status":"ready"'
request --fail --silent -X POST "$BASE_URL/api/v1/auth/register" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"name\":\"Release Smoke\"}" >/dev/null
LOGIN=$(request --fail --silent -X POST "$BASE_URL/api/v1/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(printf '%s' "$LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
test -n "$TOKEN"
ITEM=$(request --fail --silent -X POST "$BASE_URL/api/v1/items" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"type":"text","raw_text":"release smoke searchable phrase","title":"Release smoke"}')
ITEM_ID=$(printf '%s' "$ITEM" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
test -n "$ITEM_ID"
request --fail --silent "$BASE_URL/api/v1/items?q=searchable%20phrase" -H "Authorization: Bearer $TOKEN" | grep -q "$ITEM_ID"
request --fail --silent -X DELETE "$BASE_URL/api/v1/account" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "{\"password\":\"$PASSWORD\",\"confirmation\":\"DELETE\"}" >/dev/null
printf 'Smoke test passed: %s\n' "$BASE_URL"
