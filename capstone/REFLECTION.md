# Capstone — Scale & Reflect

## 1. Scale demonstration: DuckDB → Spark

Module 1 transformed the raw `admissions.csv` into three marts (`dim_bed`,
`dim_patient`, `fct_admission`) using dbt on DuckDB. For the capstone I
re-implemented that *same transform* — read, clean, type-cast, drop invalid
rows, deduplicate on `admission_id`, and aggregate into the marts — in **Apache
Spark** (`spark_capstone.py`), then compared the two outputs row-for-row:

| mart | rows | identical to DuckDB? |
|------|------|----------------------|
| `dim_bed` | 68 | ✅ |
| `dim_patient` | 1,990 | ✅ |
| `fct_admission` | 10,000 | ✅ |

The output is identical. The lesson is the important part: **the transform is
*code*, not a property of the engine.** DuckDB ran it in-process on a laptop;
Spark ran it through a distributed execution engine. The same logic that
processes 10,000 synthetic rows here would process billions across a cluster
with no change to its meaning — only the runtime changed. That portability is
exactly why "transform as code" (dbt/SQL, or framework-agnostic
DataFrame logic) matters: you choose the engine to fit the scale, not the other
way round.

> Note on running it: Spark requires JDK 17/21 (not the JDK 26 on this machine),
> so `run.sh` pins `JAVA_HOME` to OpenJDK 17. The DuckDB→Spark swap needed *no
> change* to the ontology, the loader, or any downstream module.

## 2. What this prototype is NOT

This is a **learning prototype on synthetic data, built to understand the
architecture** — not a product. Stating the boundary precisely is the point:

- **Not production-grade.** It is a teaching artifact on obviously-fake data,
  running as single laptop-scale instances. There is no SLA, no real users.
- **Not scalable as built.** A single in-memory/file DuckDB and one Fuseki
  instance comfortably handle thousands of rows; a production system handles
  billions of facts across a cluster with sharding and replication. (The Spark
  step shows the *compute* logic would carry over — the *triplestore and
  serving tier* would still need re-architecting.)
- **Not concurrency-safe.** It is single-user. The M2 action does
  validate-then-write as two steps with no transaction or lock, so two
  simultaneous admits to the same bed could both pass SHACL before either
  writes. Real systems need optimistic concurrency / transactional guarantees.
- **Not hardened.** The M3 "roles" are a stand-in for authentication: there is
  no identity provider, no sessions, no secrets management, no network policy,
  no audit accreditation (FedRAMP / IL levels). The role selector in the UI is a
  demo affordance, not a login.
- **Not integration-complete.** It ingests one clean, synthetic CSV. Production
  ingests hundreds of messy live sources with change-data-capture, schema-drift
  handling, late/duplicate data, and backfills.
- **Not operated.** No monitoring, alerting, tracing, backup/restore, HA/DR, or
  upgrade path. The in-cluster Fuseki is in-memory and loses data on restart.

None of this diminishes what was built — the value is in being able to point at
each layer, say what it demonstrates, and say exactly where the line to
production sits.

## 3. Build-vs-buy trade-off

Building this end-to-end clarifies what a commercial ontology platform actually
sells. The *concepts* are reproducible with open-source parts — an ontology
(OWL/Fuseki), validated actions (SHACL), policy-as-code security (OPA), a
grounded LLM, an app, and GitOps delivery. Wiring those into a coherent whole on
a laptop is a weekend-scale effort and is genuinely educational.

What you do **not** get by assembling them yourself is precisely the expensive
part a vendor charges for:

- **One unified, governed ontology** spanning every source — not five separate
  namespaces I hand-stitched, but a single semantic layer with managed lineage,
  versioning, and change management across the enterprise.
- **Scale, concurrency, and HA/DR** as a solved, operated property rather than a
  thing I would have to re-engineer past the prototype.
- **Security accreditation** (FedRAMP / IL levels), real authn/z, secrets, and
  audited data governance — compliance work that dwarfs the policy snippet in M3.
- **Integration depth** — hundreds of connectors, CDC, schema-drift resilience —
  and **managed operations** (monitoring, upgrades, support, SLAs).

So the trade-off is not "open-source can't do this" — clearly the building blocks
exist. It is **total cost of ownership and risk**: building the demo is cheap;
operating a governed, accredited, highly-available, integration-complete platform
at scale is the hard, ongoing, expensive part. Buy when that operated governance
and breadth is core to the business and not your differentiator; build when the
domain is narrow, the team can own the operations, and avoiding lock-in matters
more than time-to-value. The senior skill is being able to name that boundary —
which is what this whole exercise was for.
