#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[ingest-smoke] Starting compose stack (build included)..."
docker compose up -d --build

echo "[ingest-smoke] Waiting up to 60s for worker ingestion (snapshots_inserted > 0)..."
FOUND=""
for _ in $(seq 1 30); do
  LOGS="$(docker compose logs worker --tail=80 || true)"
  if echo "$LOGS" | rg -Eq 'snapshots_inserted=([1-9][0-9]*)'; then
    FOUND="yes"
    break
  fi
  sleep 2
done

if [[ -z "$FOUND" ]]; then
  echo "[ingest-smoke] Did not detect snapshots_inserted > 0 in worker logs within 60s"
  docker compose logs worker --tail=120 || true
  exit 1
fi

echo "[ingest-smoke] Worker ingestion confirmed in logs"

echo "[ingest-smoke] odds_snapshots count from Postgres:"
docker compose exec -T db psql -U postgres -d sharppicks -c "select count(*) from odds_snapshots;"

echo "[ingest-smoke] Backend health payload:"
curl -fsS http://localhost:8000/api/v1/system/health
printf '\n'
