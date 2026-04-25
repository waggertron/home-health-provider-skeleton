#!/usr/bin/env bash
#
# End-to-end smoke for the full Phase 5+6 demo loop:
#   1. Scheduler triggers Optimize Day → schedule.optimized lands.
#   2. Clinician checks in on an assigned visit → visit.status_changed lands.
#   3. Clinician sends a GPS ping → clinician.position_updated lands.
#
# Requires `make up` plus `seed_demo --enable-clinician-login` so c00@westside
# .demo has a usable password.
#
#   ./ops/full-demo.sh
#
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}
RT_URL=${RT_URL:-ws://localhost:8080}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@westside.demo}
CLI_EMAIL=${CLI_EMAIL:-c00@westside.demo}
PASSWORD=${PASSWORD:-demo1234}
TIMEOUT_MS=${TIMEOUT_MS:-25000}

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${THIS_DIR}/.." && pwd)"
RT_DIR="${REPO_ROOT}/apps/rt-node"

command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
command -v node >/dev/null || { echo "node required" >&2; exit 1; }

today=$(date -u +%Y-%m-%d)

login() {
  local email="$1"
  curl -sfS "${API_URL}/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${email}\",\"password\":\"${PASSWORD}\"}"
}

echo "→ login admin (${ADMIN_EMAIL})"
admin_login=$(login "${ADMIN_EMAIL}")
admin_access=$(jq -r .access <<<"${admin_login}")

echo "→ trigger Optimize Day so visits get assigned"
curl -sfS -X POST "${API_URL}/api/v1/schedule/${today}/optimize" \
  -H "Authorization: Bearer ${admin_access}" >/dev/null

echo "→ wait up to 30s for the solver to land assignments"
assigned_clinician=""
assigned_visit=""
for _ in $(seq 1 30); do
  sleep 1
  payload=$(curl -sfS "${API_URL}/api/v1/visits/" \
    -H "Authorization: Bearer ${admin_access}")
  read -r assigned_visit assigned_clinician < <(jq -r '
    (if type == "object" then .results else . end)
    | map(select(.status == "assigned" and .clinician != null))
    | (.[0] // empty)
    | "\(.id) \(.clinician)"
  ' <<<"${payload}") || true
  [[ -n "${assigned_visit}" ]] && break
done
[[ -n "${assigned_visit}" ]] || { echo "no assigned visit appeared — abort" >&2; exit 1; }
echo "  visit #${assigned_visit} assigned to clinician #${assigned_clinician}"

echo "→ find the clinician user (must have --enable-clinician-login on seed)"
cli_email=""
cli_access=""
slug="${ADMIN_EMAIL#admin@}"; slug="${slug%.demo}"
for n in $(seq 0 24); do
  candidate="c$(printf '%02d' "$n")@${slug}.demo"
  resp=$(curl -sfS "${API_URL}/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${candidate}\",\"password\":\"${PASSWORD}\"}" 2>/dev/null) || continue
  cid=$(jq -r '.user.clinician_id // empty' <<<"${resp}")
  if [[ "${cid}" == "${assigned_clinician}" ]]; then
    cli_email="${candidate}"
    cli_access=$(jq -r .access <<<"${resp}")
    break
  fi
done
[[ -n "${cli_email}" ]] || { echo "no clinician account matched #${assigned_clinician}" >&2; exit 1; }
echo "  ${cli_email} ↔ clinician #${assigned_clinician}"

visit_id="${assigned_visit}"

echo "→ mint scheduler ws-token"
sched_ws=$(curl -sfS -X POST "${API_URL}/api/v1/auth/ws-token" \
  -H "Authorization: Bearer ${admin_access}" | jq -r .token)

echo "→ open scheduler ws, await schedule.optimized + visit.status_changed + clinician.position_updated"
(
  cd "${RT_DIR}"
  exec node scripts/ws-multi-client.mjs "${RT_URL}/ws" "${sched_ws}" \
    "schedule.optimized,visit.status_changed,clinician.position_updated" "${TIMEOUT_MS}"
) &
watcher=$!
sleep 1

echo "→ scheduler triggers Optimize Day"
curl -sfS -X POST "${API_URL}/api/v1/schedule/${today}/optimize" \
  -H "Authorization: Bearer ${admin_access}" >/dev/null

echo "→ clinician checks in on visit #${visit_id}"
curl -sfS -X POST "${API_URL}/api/v1/visits/${visit_id}/check-in/" \
  -H "Authorization: Bearer ${cli_access}" \
  -H 'Content-Type: application/json' \
  -d '{"lat": 34.05, "lon": -118.25}' >/dev/null

echo "→ clinician sends GPS ping"
curl -sfS -X POST "${API_URL}/api/v1/positions/" \
  -H "Authorization: Bearer ${cli_access}" \
  -H 'Content-Type: application/json' \
  -d "{\"lat\": 34.06, \"lon\": -118.24, \"ts\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >/dev/null

if wait "${watcher}"; then
  echo "✓ full demo loop completed end-to-end"
else
  echo "✗ full demo smoke FAILED" >&2
  exit 1
fi
