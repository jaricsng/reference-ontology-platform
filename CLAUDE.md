# CLAUDE.md — Reference Ontology Platform (build context)

## What we are building
A working **reference implementation** of an ontology-driven operational data platform, built module by module. Full spec: `docs/mini_foundry_lab.md`. Read it before starting any module.

**This is a learning prototype on synthetic data, not a production system.** Do not add scale, HA, real auth hardening, or live integrations unless explicitly asked. The goal is a clear, working, demoable example of each architectural layer.

## Running use case (all modules share this domain)
Hospital Bed & Patient Flow — **synthetic data only, never real PHI**.
- Objects: `Patient`, `Bed`, `Ward`, `Admission`
- Links: Patient *occupiesBed* Bed; Bed *inWard* Ward
- Actions: `admit`, `discharge`, `transfer`

## Build rules (important)
1. **One module at a time.** Build, verify it actually runs, show me the output, then STOP and wait for my confirmation before starting the next module.
2. **Commit per module** with a clear message (e.g. `m0: ontology + Fuseki + SPARQL`). Keep git history clean.
3. Each module lives in its own folder: `m0-ontology/`, `m1-ingestion/`, `m2-actions/`, `m3-security/`, `m4-ai/`, `m5-app/`, `m6-infra/`.
4. Use a Python virtual environment (`.venv`); add a `requirements.txt` per module that needs Python.
5. Each module folder gets its own `README.md`: what it does, how to run it, how to verify.
6. Synthetic data only. Never invent real-looking patient identities; use obviously fake names/IDs.
7. Ask permission before destructive commands. Prefer showing a plan before large changes.

## Module plan & verification gates

### M0 — Domain & Ontology  (`m0-ontology/`)
Stack: Protégé-authored OWL/RDF + Apache Jena Fuseki + SPARQL.
Build: OWL classes (Patient/Bed/Ward/Admission), object properties, a max-cardinality-1 restriction (a Bed has at most one Patient). Load instances (3 wards, ~10 beds, a few patients) into Fuseki.
**Verify:** SPARQL query returns the free beds in a named ward, run against the live Fuseki endpoint. Show the result rows.

### M1 — Compute & Ingestion  (`m1-ingestion/`)
Stack: dbt + DuckDB → RDF loader into Fuseki.
Build: a script to generate synthetic `admissions.csv` (~10k rows). dbt project (dbt-duckdb) with staging + mart models. A Python loader mapping mart rows to the M0 ontology, emitting triples into Fuseki.
**Verify:** `dbt run` is clean and idempotent; `dbt docs generate` shows source→staging→mart lineage; triple count in Fuseki matches expected rows.

### M2 — Validation & Actions (kinetic layer)  (`m2-actions/`)
Stack: SHACL (pySHACL) + FastAPI.
Build: SHACL shapes encoding rules (no admit to an occupied bed; a patient can't occupy two beds). A FastAPI `POST /admit` endpoint: validate proposed change with SHACL → if valid, SPARQL Update → append audit log; reject invalid with a clear error.
**Verify:** valid admit updates the graph + logs; invalid admit (occupied bed) is rejected before any write; audit log records who/what/when.

### M3 — Dynamic Security  (`m3-security/`)
Stack: Open Policy Agent (OPA) + Rego.
Build: roles `ward_nurse` (own ward only) and `bed_manager` (all). Rego policy returns allow/deny + ward filter. M2 API consults OPA before bed queries and injects the ward filter into SPARQL.
**Verify:** same "show beds" request as two roles returns two correctly different result sets; policy lives outside app code.

### M4 — AI Layer  (`m4-ai/`)  [needs local Docker/Ollama — runs on my machine]
Stack: Ollama (local LLM, e.g. llama3.2) + LangChain.
Build: chain that takes the ontology schema as context → question → generates SPARQL → executes against Fuseki → summarises rows in plain language. Route generated queries through the M3 security filter.
**Verify:** agent produces valid SPARQL for ≥3 distinct questions; answers correct vs ground truth; security filter applied (no permission bypass). Keep questions within the modelled domain.

### M5 — Application  (`m5-app/`)
Stack: Streamlit (fast path) or Next.js (if I ask for the TypeScript stack).
Build: dashboard showing live ward occupancy (querying Fuseki); Admit/Discharge controls calling the M2 action API; view scoped by role (M3).
**Verify:** dashboard reflects current triplestore state; buttons invoke the validated action API; role scoping visible; rejected actions handled gracefully.

### M6 — Infrastructure & Delivery  (`m6-infra/`)  [needs local Docker/k3d — runs on my machine]
Stack: k3d (local Kubernetes) + Argo CD (GitOps).
Build: Dockerfiles for the M2 API, M4 agent, M5 app (Fuseki has an official image). k8s manifests (Deployments, Services). k3d cluster. Argo CD Application pointing at the manifests in this Git repo.
**Verify:** all components run as pods, reachable via services; Argo CD shows Synced/Healthy; a Git commit (e.g. replica bump) triggers an automatic reconcile.

### Capstone — Scale & Reflect
Swap M1's DuckDB transform for an equivalent Spark job on k3d; confirm identical output (logic was portable, only the engine changed). Then write the required "what this is NOT" statement and build-vs-buy reflection (see lab capstone section).

## Tech notes
- All tools are free/open-source: Kubernetes/k3d, Fuseki, DuckDB, dbt-core, OPA, Ollama, FastAPI, Streamlit, Argo CD (Apache 2.0).
- Fuseki SPARQL endpoint default: `http://localhost:3030/<dataset>`.
- Keep secrets out of git. Add a `.gitignore` early (`.venv/`, `__pycache__/`, `*.db`, `.env`, dbt `target/`).
- Prefer small, readable code over cleverness — this repo is a teaching/portfolio artifact and may be read by an interviewer.

## Definition of done (whole repo)
Every module folder runs from its README; top-level README explains the architecture and links each module; clean per-module commit history; the M0–M5 chain works end-to-end on one machine; M6 deploys it to k3d via Argo CD; capstone reflection written.
