#!/usr/bin/env bash
# Run the "free beds in a ward" SPARQL query against the live Fuseki endpoint.
# Run serve.sh + load.sh first.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENDPOINT="${FUSEKI_ENDPOINT:-http://localhost:3030/hospital}"
QUERY_FILE="${1:-$DIR/queries/free-beds-in-ward.rq}"

echo "Query: $QUERY_FILE"
echo "Endpoint: $ENDPOINT/sparql"
echo "----------------------------------------"
curl -fsS -H 'Accept: text/csv' \
     --data-urlencode "query=$(cat "$QUERY_FILE")" \
     "$ENDPOINT/sparql"
