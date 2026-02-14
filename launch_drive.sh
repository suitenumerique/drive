#!/usr/bin/env bash
set -euo pipefail

NETWORK_NAME="lasuite-network"
WAIT_TIMEOUT_SECS="${WAIT_TIMEOUT_SECS:-1200}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export DOCKER_USER="${DOCKER_USER:-$(id -u)}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is not installed or not in PATH" >&2
  exit 127
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "error: docker compose is not available" >&2
  exit 127
fi

mkdir -p data/media data/static env.d/development
touch \
  env.d/development/crowdin.local \
  env.d/development/common.local \
  env.d/development/postgresql.local \
  env.d/development/kc_postgresql.local

# Next.js writes build/dev artifacts under `.next/`. If this directory was created
# previously by a different UID (e.g. after running docker as root), `next dev`
# may crash with EACCES. This folder is safe to delete.
rm -rf ./src/frontend/apps/drive/.next 2>/dev/null || true

if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "Creating external Docker network: $NETWORK_NAME"
  docker network create "$NETWORK_NAME" >/dev/null
else
  echo "External Docker network already exists: $NETWORK_NAME"
fi

echo "Starting Drive stack..."
docker compose --profile frontend up -d --build --wait --wait-timeout "${WAIT_TIMEOUT_SECS}"

echo "Seeding database (migrations + i18n + WOPI config)..."
docker compose run --rm app-dev python manage.py migrate --no-input
docker compose run --rm app-dev python manage.py compilemessages --ignore=".venv/**/*"
docker compose run --rm app-dev python manage.py trigger_wopi_configuration

if command -v curl >/dev/null 2>&1; then
  host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"

  echo "Waiting for frontend to respond on :3000..."
  for i in {1..60}; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ || true)"
    if [ "${code}" = "200" ]; then
      break
    fi
    sleep 2
  done

  if [ -n "${host_ip}" ]; then
    echo "Frontend (LAN) check: http://${host_ip}:3000"
    curl -sS -o /dev/null -w 'status=%{http_code}\n' "http://${host_ip}:3000/" || true
  fi
fi
