#!/usr/bin/env bash
# rebuild-deploy.sh — LOCAL dev rebuild for Docker Desktop (port 8787).
#
# NOT used for production. Production deploys run on the VPS:
#   ssh root@195.35.8.46 'cd /opt/tasks-tracker && git pull --ff-only \
#     && docker compose up -d --build'
# (docker-compose.override.yml there binds 127.0.0.1:8790:8787 behind Caddy
#  at https://tasksmgr.rogeriogt.com, REQUIRE_AUTH=true)
#
# Local mode = no auth required (local pseudo-user), data in ./data volume.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8787}"

echo "==> Switching to Docker Desktop context"
docker context use desktop-linux >/dev/null 2>&1 || \
  docker context use default >/dev/null 2>&1 || true

echo "==> Building image (frontend is built inside the Dockerfile multi-stage)"
docker compose up -d --build --remove-orphans

echo "==> Waiting for health check on http://localhost:${PORT}/api/health"
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
    echo "==> OK — app is live: http://localhost:${PORT}"
    exit 0
  fi
  sleep 1
done

echo "==> Health check failed. Last 50 log lines:"
docker compose logs --tail=50
exit 1
