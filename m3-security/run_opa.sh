#!/usr/bin/env bash
# Run OPA as a policy decision server on :8181, loading the Rego policy + data.
# Decision endpoint: POST http://localhost:8181/v1/data/hospital/authz/decision
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
OPA="$REPO/tools/opa"

if [[ ! -x "$OPA" ]]; then
  echo "OPA not found at $OPA — see m3-security/README.md for the download step." >&2
  exit 1
fi

echo "Starting OPA on :8181 (policy: m3-security/policy/)"
exec "$OPA" run --server --addr 127.0.0.1:8181 "$DIR/policy/"
