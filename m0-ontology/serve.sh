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

# Persistent TDB2 dataset on disk, so loaded triples survive a restart.
# The directory is regenerable from the .ttl files, so it is gitignored.
DB_DIR="$REPO_ROOT/tools/fuseki-db/hospital"
mkdir -p "$DB_DIR"

echo "Starting Fuseki — endpoint: http://localhost:3030/hospital (TDB2: $DB_DIR)"
exec "$FUSEKI_HOME/fuseki-server" --tdb2 --loc="$DB_DIR" --update /hospital
