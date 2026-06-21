#!/usr/bin/env bash
# Start the Module 2 action API (FastAPI + uvicorn).
# Prereq: Fuseki running (m0-ontology/serve.sh) with M1 data loaded.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"

cd "$DIR"
echo "Action API -> http://127.0.0.1:8000  (docs at /docs)"
exec "$REPO/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 "$@"
