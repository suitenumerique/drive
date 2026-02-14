#!/usr/bin/env bash
set -euo pipefail

NETWORK_NAME="lasuite-network"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export DOCKER_USER="${DOCKER_USER:-$(id -u)}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is not installed or not in PATH" >&2
  exit 127
fi

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
docker compose --profile frontend up -d --build
