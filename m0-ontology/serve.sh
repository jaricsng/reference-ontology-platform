#!/usr/bin/env bash
# Start Apache Jena Fuseki with an in-memory dataset named /hospital.
# Endpoint: http://localhost:3030/hospital
# Stop with Ctrl-C. Data is reloaded each start via load.sh (it is in-memory).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUSEKI_HOME="$REPO_ROOT/tools/apache-jena-fuseki-6.1.0"

if [[ ! -x "$FUSEKI_HOME/fuseki-server" ]]; then
  echo "Fuseki not found at $FUSEKI_HOME — see m0-ontology/README.md for the download step." >&2
  exit 1
fi

# Keep Fuseki's runtime working dir out of the (versioned) module folder.
export FUSEKI_BASE="$REPO_ROOT/tools/fuseki-base"
mkdir -p "$FUSEKI_BASE"

echo "Starting Fuseki — endpoint: http://localhost:3030/hospital"
exec "$FUSEKI_HOME/fuseki-server" --mem --update /hospital
