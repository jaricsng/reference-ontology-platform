#!/usr/bin/env bash
# Load the M1 synthetic data into the in-cluster Fuseki (in-memory dataset).
# Re-run after a Fuseki pod restart.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

kubectl -n hospital rollout status deploy/fuseki --timeout=180s
echo "==> Port-forwarding Fuseki and loading data"
kubectl -n hospital port-forward svc/fuseki 3030:3030 >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true' EXIT
sleep 4

FUSEKI_ENDPOINT="http://localhost:3030/hospital" \
  "$REPO/.venv/bin/python" "$REPO/m1-ingestion/load_to_fuseki.py"
