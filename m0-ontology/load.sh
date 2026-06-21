#!/usr/bin/env bash
# Load the ontology (TBox) and instance data (ABox) into the running
# Fuseki dataset via the SPARQL Graph Store HTTP Protocol.
# Run serve.sh in another terminal first.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENDPOINT="${FUSEKI_ENDPOINT:-http://localhost:3030/hospital}"

echo "Loading ontology + data into $ENDPOINT (default graph) ..."
# Clear first so re-running against the persistent store stays idempotent.
curl -fsS -X POST -H 'Content-Type: application/sparql-update' \
     --data 'DROP DEFAULT' "$ENDPOINT/update" >/dev/null
curl -fsS -X POST -H 'Content-Type: text/turtle' \
     --data-binary "@$DIR/ontology/hospital-ontology.ttl" \
     "$ENDPOINT/data?default" >/dev/null
curl -fsS -X POST -H 'Content-Type: text/turtle' \
     --data-binary "@$DIR/data/hospital-data.ttl" \
     "$ENDPOINT/data?default" >/dev/null

# Report the triple count so it can be checked against expectations.
COUNT=$(curl -fsS -H 'Accept: text/csv' \
     --data-urlencode 'query=SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }' \
     "$ENDPOINT/sparql" | tail -1)
echo "Loaded. Triple count in store: $COUNT"
