#!/usr/bin/env bash
# Build the platform images and import them into the k3d cluster (no registry).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER="${CLUSTER:-hospital}"

echo "==> Building images"
docker build -t hospital/fuseki:local     "$REPO/m6-infra/images/fuseki"
docker build -t hospital/action-api:local "$REPO/m2-actions"
docker build -t hospital/agent:local      "$REPO/m4-ai"
docker build -t hospital/app:local        "$REPO/m5-app"

echo "==> Importing images into k3d cluster '$CLUSTER'"
k3d image import -c "$CLUSTER" \
  hospital/fuseki:local hospital/action-api:local hospital/agent:local hospital/app:local
echo "Done."
