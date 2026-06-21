# M0 — Domain & Ontology

The semantic core of the platform: a formal OWL model of the Hospital Bed &
Patient Flow domain, loaded into an Apache Jena Fuseki triplestore and queried
with SPARQL.

**Synthetic data only — never real PHI.**

## What this module contains

| Path | What it is |
|------|------------|
| `ontology/hospital-ontology.ttl` | The **TBox** — classes, object properties, and the max-cardinality rule (the *types* and *rules*). |
| `data/hospital-data.ttl` | The **ABox** — instances: 3 wards, 10 beds, 5 synthetic patients (the *individuals*). |
| `queries/free-beds-in-ward.rq` | The deliverable SPARQL query: free beds in a named ward. |
| `serve.sh` | Start Fuseki with a **persistent** (TDB2 on-disk) `/hospital` dataset. |
| `load.sh` | Upload the ontology + data into the running dataset. |
| `query.sh` | Run the free-beds query against the live endpoint. |

### The model

- **Classes:** `Patient`, `Bed`, `Ward`, `Admission`.
- **Object properties:** `occupiesBed` (Patient → Bed), `inWard` (Bed → Ward),
  and `occupiedBy` (Bed → Patient, the inverse of `occupiesBed`).
- **Restriction:** `Bed ⊑ occupiedBy max 1 Patient` — a bed is occupied by **at
  most one** patient. This is the domain invariant the rest of the platform
  protects. (`occupiesBed` and `inWard` are also `FunctionalProperty`: a patient
  occupies at most one bed; a bed sits in exactly one ward.)

### Class vs instance

`Bed` is a **class** — the *type* "bed", with its rules. `:bed-a3` is an
**instance** — one specific bed in Ward A. The TBox file defines classes; the
ABox file defines instances of them.

## Prerequisites

- **Java 17+** on your `PATH` (`java -version`). Fuseki is a Java service.
- **Apache Jena Fuseki 6.1.0**, expected at
  `../tools/apache-jena-fuseki-6.1.0/`. It is a downloaded binary (gitignored),
  not source. To (re)install from the repo root:

  ```bash
  mkdir -p tools
  curl -sSL https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-6.1.0.tar.gz \
    | tar -xz -C tools/
  ```

> Protégé is the spec's suggested *authoring* tool, but the actual artifact is
> the Turtle file. The ontology here is hand-authored Turtle and opens cleanly
> in Protégé if you want to run the HermiT reasoner (see "Validation" below).

## How to run

Three terminals, or background the server. From `m0-ontology/`:

```bash
# 1. Start the triplestore (leave running)
./serve.sh
#    -> endpoint at http://localhost:3030/hospital
#    -> admin UI  at http://localhost:3030/

# 2. Load ontology + data
./load.sh

# 3. Run the deliverable query
./query.sh
```

## How to verify

Loading reports the triple count, and the query returns the free beds in Ward A:

```
$ ./load.sh
Loaded. Triple count in store: 88

$ ./query.sh
bed,bedLabel
http://example.org/hospital#bed-a3,Bed A3
http://example.org/hospital#bed-a4,Bed A4
```

**Why A3 and A4?** Ward A has 4 beds (A1–A4); patients occupy A1 and A2, so A3
and A4 are free. Per-ward free counts: Ward A = 2, Ward B = 2, ICU = 1.

### Assessment criteria → evidence

- [x] **Ontology loads without errors** — `load.sh` loads all 88 triples; Fuseki
  rejects malformed Turtle, so a clean load is the parse check.
- [x] **At-most-one-patient restriction present** — confirm it is in the store:
  ```bash
  curl -s -H 'Accept: text/csv' --data-urlencode 'query=
    PREFIX owl:<http://www.w3.org/2002/07/owl#>
    PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?onClass ?onProperty ?maxCard WHERE {
      ?onClass rdfs:subClassOf ?r .
      ?r a owl:Restriction; owl:onProperty ?onProperty; owl:maxCardinality ?maxCard }' \
    http://localhost:3030/hospital/sparql
  # -> Bed, occupiedBy, 1
  ```
- [x] **"Free beds in Ward A" returns correct results** — `./query.sh` → A3, A4.
- [x] **Class vs instance** — explained above.

### Validation note (OWL vs enforcement)

The max-cardinality restriction *describes* a valid state. To **prove** it has
teeth, open `hospital-ontology.ttl` + `hospital-data.ttl` in Protégé, assert a
second patient into one bed (`:pat-006 :occupiesBed :bed-a3`), and run HermiT —
the reasoner reports the ontology inconsistent.

Crucially, OWL's open-world reasoning *detects* that contradiction; it does not
*prevent the write*. Stopping a bad admit at write time is a closed-world job,
which is exactly what **Module 2** adds with SHACL behind a FastAPI action. M0
establishes the model; M2 enforces it.

## Persistence

The dataset is a **persistent TDB2 store** on disk at
`tools/fuseki-db/hospital/` (regenerable from the `.ttl` files, so gitignored).
Loaded triples survive a server restart — `load.sh` is needed only once (or
after you change the source data). `load.sh` clears the default graph before
loading, so it is idempotent: re-running keeps the count at 88. Later modules
(M1 onward) write into this same persistent store.

To start fresh, stop Fuseki and `rm -rf tools/fuseki-db`.

## Stopping Fuseki

If started via `serve.sh`, press Ctrl-C. Data remains on disk for the next start.
