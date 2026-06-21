# M2 — Validation & Actions (Kinetic Layer)

The platform **Action** pattern: a *guarded state transition*. An `admit` is not
a raw write — it is **validate → write → log**. The model (M0) describes valid
states; this module *enforces* them on every write with SHACL behind a FastAPI
endpoint.

**Synthetic data only — never real PHI.**

## Why OWL needs SHACL here

OWL is **open-world**: from "we haven't said this bed is free" it concludes
nothing, and its cardinality axioms *infer* (or detect contradiction) rather
than *block a write*. To stop a bad admit you need a **closed-world** check on a
concrete graph: SHACL. So the action builds the *proposed* graph (current
occupancy + the new triple) and validates it with pySHACL **before** committing.

## What this module contains

| Path | What it is |
|------|------------|
| `shapes/hospital-shapes.ttl` | SHACL shapes for the two business rules. |
| `app/main.py` | FastAPI app: `/admit`, `/discharge`, `/beds`, `/audit`, `/health`. |
| `app/shacl_check.py` | Runs pySHACL on a proposed graph. |
| `app/sparql.py` | Fuseki client + URI helpers (match the M1 loader). |
| `app/audit.py` | Append-only JSONL audit log (who/what/when/outcome). |
| `test_actions.py` | End-to-end verification of the guard. |
| `run.sh` | Start the API with uvicorn. |

### The business rules (SHACL)

1. **A patient cannot occupy more than one bed** — `sh:targetSubjectsOf
   :occupiesBed`, `:occupiesBed sh:maxCount 1`.
2. **A bed cannot be occupied by more than one patient** (no admit to an
   occupied bed) — `sh:targetObjectsOf :occupiesBed`, inverse-path
   `:occupiesBed sh:maxCount 1`.

Using `targetSubjectsOf`/`targetObjectsOf` lets the rules validate the occupancy
triples directly, so we only ship the relevant subgraph to the validator.

### The `admit` flow

```
POST /admit {patient_id, bed_code, actor}
   ├─ bed exists?            no → 404 (+ audit "rejected")
   ├─ build proposed graph = current occupancy + (patient occupiesBed bed)
   ├─ SHACL validate
   │     conforms = false →  409 with the rule message, NO write (+ audit "rejected")
   │     conforms = true  →  SPARQL Update: insert occupancy + a new :Admission
   └─ append audit entry "success" → 200
```

## Prerequisites

- Repo venv on Python 3.12 with deps: `.venv/bin/pip install -r m2-actions/requirements.txt`
- **Fuseki running with M1 data loaded** (`m0-ontology/serve.sh`, then `m1-ingestion/run.sh`).

## How to run

```bash
# terminal 1: Fuseki              ./m0-ontology/serve.sh
# (once)    : load data           ./m1-ingestion/run.sh
# terminal 2: action API          ./m2-actions/run.sh    # -> http://127.0.0.1:8000/docs
```

Try it:
```bash
# a free bed (use /beds to find one), then:
curl -s -X POST localhost:8000/admit -H 'Content-Type: application/json' \
  -d '{"patient_id":"SYN-PTEST1","bed_code":"A4","actor":"nurse_jane"}'

# same bed again -> rejected
curl -s -X POST localhost:8000/admit -H 'Content-Type: application/json' \
  -d '{"patient_id":"SYN-PTEST9","bed_code":"A4","actor":"nurse_jane"}'
```

## How to verify

With the API running:

```bash
.venv/bin/python m2-actions/test_actions.py
```

Expected (12 checks, all pass):

```
A. valid admit to a free bed            -> 200, bed now occupied
B. admit to an already-occupied bed     -> 409, occupant unchanged (no write)
C. admit a patient who already has a bed -> 409
D. discharge frees the bed              -> 200
E. audit log records who/what/when      -> success + rejected entries, timestamps
RESULT: 12 passed, 0 failed ✅
```

Sample audit entries (`m2-actions/audit/audit-log.jsonl`):

```
… nurse_jane admit     success   patient=SYN-PTEST1 bed=ICU-10  admission adm-live-…
… nurse_jane admit     rejected  patient=SYN-PTEST2 bed=ICU-10  A bed cannot be occupied by more than one patient …
… nurse_jane admit     rejected  patient=syn-p00593 bed=ICU-12  A patient cannot occupy more than one bed.
… nurse_jane discharge success   patient=syn-ptest1 bed=ICU-10  bed freed
```

### Assessment criteria → evidence

- [x] **Valid admit updates the graph and logs the action** — case A + audit.
- [x] **Invalid admit (occupied bed) is rejected before any write** — case B: 409
  and the occupant is unchanged; no `occupiesBed` triple is written.
- [x] **Audit log records who/what/when** — `actor`, `action`, `patient`, `bed`,
  `outcome`, ISO-8601 `ts` per entry.
- [x] **Why open-world OWL needs closed-world SHACL** — see top of this README.

> Note: this is single-user and not concurrency-safe — validate-then-write is
> not atomic across simultaneous requests. That limit is intentional for the
> prototype and is named explicitly in the capstone "what this is NOT".
