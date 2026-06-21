# Reference Ontology Platform

A working **reference implementation** of an ontology-driven operational data
platform, built one stack layer at a time. The running domain is **Hospital Bed
& Patient Flow** — modelled, validated, secured, queried, and deployed.

> ⚠️ **This is a learning prototype on synthetic data, not a production system.**
> It demonstrates every architectural layer end-to-end on one laptop. It is not
> built for scale, concurrency, real auth, or live integrations. The capstone
> makes that gap an explicit, assessed outcome.

Full lab spec: [`docs/mini_foundry_lab.md`](docs/mini_foundry_lab.md).
Build context & rules: [`CLAUDE.md`](CLAUDE.md).

## Architecture (built module by module)

| Module | Layer | Stack | Status |
|--------|-------|-------|--------|
| [M0 — Domain & Ontology](m0-ontology/) | Semantic model | OWL/RDF + Fuseki + SPARQL | ✅ done |
| [M1 — Compute & Ingestion](m1-ingestion/) | Data plane | dbt + DuckDB → triplestore | ✅ done |
| [M2 — Validation & Actions](m2-actions/) | Kinetic | SHACL + FastAPI | ✅ done |
| [M3 — Dynamic Security](m3-security/) | Per-object security | OPA + Rego | ✅ done |
| M4 — AI Layer | Grounded AI | Ollama + LangChain | ⬜ |
| M5 — Application | Presentation | Streamlit / Next.js | ⬜ |
| M6 — Infra & Delivery | Substrate + GitOps | k3d + Argo CD | ⬜ |
| Capstone | Scale & reflect | DuckDB → Spark | ⬜ |

Each module folder has its own `README.md` with run + verify steps.

## Domain

- **Objects:** `Patient`, `Bed`, `Ward`, `Admission`
- **Links:** Patient *occupiesBed* Bed; Bed *inWard* Ward
- **Actions:** `admit`, `discharge`, `transfer`
- **Data:** synthetic only — obviously-fake names/IDs, never real PHI.

## Repo layout

```
m0-ontology/ … m6-infra/   one folder per module
docs/                       lab spec + portfolio guide
tools/                      downloaded binaries (Fuseki) — gitignored
.venv/                      Python virtualenv — gitignored
```

## Getting started

Start with [M0](m0-ontology/README.md). Each subsequent module builds on the
live triplestore from M0.
