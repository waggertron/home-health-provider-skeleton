#!/usr/bin/env bash
# End-to-end smoke test: boot compose from scratch, assert health,
# assert seeded admin can log in. Used by CI and local verification.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "→ copying .env.example → .env"
  cp .env.example .env
fi

echo "→ building and starting stack…"
docker compose up -d --build

echo "→ waiting for api-django health…"
for i in {1..60}; do
  if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    break
  fi
  sleep 1
done

echo "→ asserting health body…"
HEALTH=$(curl -sf http://localhost:8000/api/v1/health)
echo "$HEALTH" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'
echo "$HEALTH" | grep -Eq '"tenant"[[:space:]]*:[[:space:]]*null'

echo "→ asserting seeded admin login…"
RESPONSE=$(curl -sf -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@westside.demo","password":"demo1234"}')

echo "$RESPONSE" | grep -q '"access"'
echo "$RESPONSE" | grep -q '"refresh"'
echo "$RESPONSE" | grep -Eq '"role"[[:space:]]*:[[:space:]]*"admin"'

echo "✓ Phase 1 smoke test passed"
