# M1 — Compute & Ingestion

The data plane: take messy tabular data and turn it into clean, modelled
instances in the triplestore — **transform as code**. Raw synthetic CSV →
dbt + DuckDB (staging + marts, with lineage) → an RDF loader that maps mart
rows to the M0 ontology and writes triples into Fuseki.

**Synthetic data only — never real PHI.**

## What this module contains

| Path | What it is |
|------|------------|
| `generate_admissions.py` | Generates `data/raw/admissions.csv` — 10,000 clean admissions + deliberate dirty rows. |
| `hospital_ingest/` | dbt project (dbt-duckdb): source → staging → marts. |
| `hospital_ingest/models/staging/stg_admissions.sql` | Clean types, trim/normalise, drop invalid, **dedupe**. |
| `hospital_ingest/models/marts/` | `dim_bed`, `dim_patient`, `fct_admission`. |
| `ontology/hospital-admissions.ttl` | M1 extension to the M0 ontology: admission properties. |
| `load_to_fuseki.py` | Reads marts from DuckDB → emits RDF → replaces the Fuseki default graph → verifies counts. |
| `run.sh` | One command for the whole pipeline. |

## The pipeline

```
admissions.csv ──source──▶ stg_admissions ──▶ dim_bed
 (raw, dirty)              (clean, deduped)  ├─▶ dim_patient
                                             └─▶ fct_admission ──load──▶ Fuseki (RDF)
```

- **Source:** the CSV is a real dbt *source* (dbt-duckdb external location), so
  it shows up as the root of the lineage graph.
- **Staging** (`view`): casts timestamps, trims whitespace, upper-cases bed
  codes, drops rows with blank ids, and dedupes on `admission_id`
  (`row_number() … = 1`). This is **schema-on-write**: the data is shaped *once*
  here, so everything downstream can trust it.
- **Marts** (`table`): the dimensional model — `dim_bed` (one row per bed + its
  ward), `dim_patient`, `fct_admission` (one row per admission, with `status`
  = current/discharged).

### Mapping to the ontology

| Mart | Ontology |
|------|----------|
| distinct `ward_name` | `:Ward` (`rdfs:label`) |
| `dim_bed` | `:Bed` + `:inWard` |
| `dim_patient` | `:Patient` |
| `fct_admission` | `:Admission` + `:admissionPatient` / `:admissionBed` / `:admittedAt` / `:dischargedAt` / `:admissionStatus` |
| `fct_admission` where `status='current'` | `:occupiesBed` (live occupancy) |

The loader generates data so that **at most one current admission exists per
bed**, and each current occupant is a distinct patient — so the live occupancy
respects the M0 "a bed holds at most one patient" rule.

## Prerequisites

- The repo venv on **Python 3.12** (dbt does not yet support 3.13/3.14):
  ```bash
  /usr/local/bin/python3.12 -m venv .venv      # from repo root
  .venv/bin/pip install -r m1-ingestion/requirements.txt
  ```
- **Fuseki running** with the persistent dataset: `m0-ontology/serve.sh`.

## How to run

```bash
# from the repo root, with Fuseki already running:
./m1-ingestion/run.sh
```

This generates the CSV, runs dbt (build + test + docs), then loads RDF into
Fuseki and verifies the triple counts.

To explore the lineage graph in a browser:
```bash
cd m1-ingestion/hospital_ingest
../../.venv/bin/dbt docs generate --profiles-dir .
../../.venv/bin/dbt docs serve   --profiles-dir .   # opens the DAG at localhost:8080
```

> **Note:** `run.sh` replaces the Fuseki default graph with the full M1 dataset,
> superseding M0's small hand-authored sample. The ontology (schema) is reused;
> only the instance data changes. To get M0's tiny demo back, run
> `m0-ontology/load.sh`.

## How to verify

Expected output of `run.sh` (counts are deterministic via a fixed seed):

```
dbt run  -> PASS=4   (stg_admissions, dim_bed, dim_patient, fct_admission)
dbt test -> PASS=17  (unique/not_null/relationships/accepted_values)

Verification — Fuseki triplestore vs dbt mart row counts
  [OK ] Ward instances          fuseki=4      expected=4
  [OK ] Bed instances           fuseki=68     expected=68
  [OK ] Patient instances       fuseki=1990   expected=1990
  [OK ] Admission instances     fuseki=10000  expected=10000
  [OK ] Current occupancy       fuseki=44     expected=44
  Total triples in store: 64259 (built graph: 64259)
RESULT: ALL CHECKS PASSED ✅
```

### Assessment criteria → evidence

- [x] **dbt models run cleanly and are idempotent** — `dbt build` re-runs to the
  same result (fixed-seed CSV; marts are full rebuilds; `unique` test on
  `stg_admissions.admission_id` proves the dedupe).
- [x] **Lineage shows source → staging → mart** — `dbt docs generate`; the
  manifest's parent map is `admissions → stg_admissions → fct_admission`.
- [x] **Triple count matches expected row counts** — the loader cross-checks each
  class's instance count in Fuseki against the mart row counts (above).
- [x] **Schema-on-write vs schema-on-read** — see below.

The M0 deliverable query still works unchanged against this larger dataset:

```bash
./m0-ontology/query.sh          # free beds in Ward A — now 10 of 20
```

### Schema-on-write vs schema-on-read

Here we do **schema-on-write**: dbt cleans, types, and dedupes the data *before*
it lands as triples, so every consumer reads a guaranteed shape. The alternative,
**schema-on-read**, stores raw data as-is and applies structure at query time —
flexible, but every reader must re-handle the mess. This module deliberately
pays the cost once, on write, so M2–M5 can trust the model.
