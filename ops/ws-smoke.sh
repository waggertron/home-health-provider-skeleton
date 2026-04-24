#!/usr/bin/env bash
#
# End-to-end smoke test for the Phase 4 realtime path:
#   login → mint WS token → connect WS → trigger optimize →
#   assert a schedule.optimized frame arrives within 5s.
#
# Run against `make up` stack (Django on 8000, rt-node on 8080):
#
#   ./ops/ws-smoke.sh
#
# Env overrides: API_URL, RT_URL, EMAIL, PASSWORD, TIMEOUT_MS.
#
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
RT_URL=${RT_URL:-ws://localhost:8080}
EMAIL=${EMAIL:-admin@westside.demo}
PASSWORD=${PASSWORD:-demo1234}
# Solver budget defaults to 10s; allow 15s for the full round-trip.
TIMEOUT_MS=${TIMEOUT_MS:-15000}

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${THIS_DIR}/.." && pwd)"
RT_DIR="${REPO_ROOT}/apps/rt-node"

command -v jq  >/dev/null || { echo "jq required" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
command -v node >/dev/null || { echo "node required" >&2; exit 1; }

today=$(date -u +%Y-%m-%d)

echo "→ login ${EMAIL}"
access=$(curl -sfS "${API_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" | jq -r .access)

echo "→ mint ws-token"
ws_token=$(curl -sfS -X POST "${API_URL}/api/v1/auth/ws-token" \
  -H "Authorization: Bearer ${access}" | jq -r .token)

echo "→ open ws, wait for schedule.optimized"
(
  cd "${RT_DIR}"
  exec node scripts/ws-client.mjs "${RT_URL}/ws" "${ws_token}" schedule.optimized "${TIMEOUT_MS}"
) &
smoke_pid=$!
# Give the client a beat to connect + subscribe before we trigger the solve.
sleep 1

echo "→ POST /schedule/${today}/optimize"
curl -sfS -X POST "${API_URL}/api/v1/schedule/${today}/optimize" \
  -H "Authorization: Bearer ${access}" >/dev/null

if wait "${smoke_pid}"; then
  echo "✓ schedule.optimized received within ${TIMEOUT_MS}ms"
else
  echo "✗ smoke test FAILED" >&2
  exit 1
fi
