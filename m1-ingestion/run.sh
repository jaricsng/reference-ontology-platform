#!/usr/bin/env bash
# Module 1 pipeline: synthetic CSV -> dbt (DuckDB) -> RDF loader -> Fuseki.
# Prereq: Fuseki running (m0-ontology/serve.sh) and the repo venv active/available.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
PY="$REPO/.venv/bin/python"
DBT="$REPO/.venv/bin/dbt"

export M1_RAW_CSV="$DIR/data/raw/admissions.csv"
export M1_DUCKDB="$DIR/hospital_ingest/hospital.duckdb"

echo "==> 1/5  Generate synthetic admissions.csv"
"$PY" "$DIR/generate_admissions.py"

cd "$DIR/hospital_ingest"
echo; echo "==> 2/5  dbt run (build staging + marts)"
"$DBT" run --profiles-dir .

echo; echo "==> 3/5  dbt test (quality + idempotency checks)"
"$DBT" test --profiles-dir .

echo; echo "==> 4/5  dbt docs generate (source -> staging -> mart lineage)"
"$DBT" docs generate --profiles-dir . >/dev/null
echo "    docs built in hospital_ingest/target/ (serve with: dbt docs serve --profiles-dir .)"

echo; echo "==> 5/5  Load marts into Fuseki as RDF + verify counts"
"$PY" "$DIR/load_to_fuseki.py"
