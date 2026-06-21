# Capstone — Scale & Reflect

Two deliverables: (1) a **scale demonstration** that re-runs the Module 1
transform in Apache Spark and proves the output is identical to the dbt/DuckDB
version, and (2) a written **gap-and-trade-off analysis** including the required
"what this is NOT" statement.

**Synthetic data only — never real PHI.**

## What this contains

| Path | What it is |
|------|------------|
| `spark_capstone.py` | The Spark re-implementation of the M1 transform + a row-for-row comparison against the DuckDB marts. |
| `run.sh` | Runs it with JDK 17 (Spark does not support the JDK 26 on this machine). |
| `REFLECTION.md` | The assessed write-up: scale lesson, gaps, "what this is NOT", build-vs-buy. |

## Prerequisites

- M1 already run (provides `m1-ingestion/data/raw/admissions.csv` and the dbt
  marts in `m1-ingestion/hospital_ingest/hospital.duckdb`).
- **JDK 17** (Spark is incompatible with JDK 26): `brew install openjdk@17`.
- Repo venv deps: `.venv/bin/pip install -r capstone/requirements.txt`.

## How to run

```bash
./capstone/run.sh
```

## How to verify

Expected output:

```
Spark 4.1.2 — running the M1 transform on admissions.csv
mart              spark rows   duckdb rows    identical?
--------------------------------------------------------
dim_bed                   68            68         YES ✅
dim_patient             1990          1990         YES ✅
fct_admission          10000         10000         YES ✅
--------------------------------------------------------
RESULT: Spark output is IDENTICAL to the DuckDB version ✅
```

It also writes the Spark marts as Parquet to `capstone/output/` (gitignored).

### Assessment criteria → evidence

- [x] **Spark pipeline output matches the DuckDB version** — row-for-row equal
  for all three marts (above).
- [x] **Reflection identifies ≥4 real production gaps** — see `REFLECTION.md` §2
  (scale, concurrency, hardening, integration, operations, …).
- [x] **"What this is NOT" statement present, accurate, own words** — `REFLECTION.md` §2.
- [x] **Build-vs-buy trade-off with nuance** — `REFLECTION.md` §3.

## The takeaway

The transform is *code*, independent of the engine: DuckDB ran it in-process,
Spark ran it distributed, the marts are identical. Only the compute tier would
change to scale to billions of rows — the ontology, loader, actions, security,
AI, and app are untouched.
