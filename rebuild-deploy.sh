#!/usr/bin/env bash
# rebuild-deploy.sh — rebuild and redeploy the tasks tracker on Docker Desktop.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8787}"

echo "==> Switching to Docker Desktop context"
docker context use desktop-linux >/dev/null 2>&1 || \
  docker context use default >/dev/null 2>&1 || true

echo "==> Building image"
docker compose build

echo "==> Deploying container"
docker compose up -d --build

echo "==> Waiting for health check on http://localhost:${PORT}/api/health"
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
    echo "==> OK — app is live: http://localhost:${PORT}"
    exit 0
  fi
  sleep 1
done

echo "==> Health check failed. Last 50 log lines:"
docker compose logs --tail=50
exit 1
