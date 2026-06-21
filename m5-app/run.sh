#!/usr/bin/env bash
# Start the M5 Next.js dashboard (dev mode) on http://localhost:3000
# Prereqs: Fuseki (M0), OPA (M3), action API (M2); optional: agent service (M4).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ ! -d node_modules ]]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Dashboard -> http://localhost:3000"
echo "Backends:  action API ${ACTION_API:-http://127.0.0.1:8000} · agent ${AGENT_API:-http://127.0.0.1:8002}"
exec npm run dev
