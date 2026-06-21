#!/usr/bin/env python3
"""Load the dbt marts into Fuseki as RDF, mapped to the M0 ontology.

Reads dim_bed / dim_patient / fct_admission from the DuckDB database that
`dbt run` produced, builds the ontology + instance triples with rdflib, and
replaces the Fuseki default graph with them (idempotent PUT).

Mapping (mart row -> ontology):
  ward_name                 -> :Ward                (rdfs:label)
  dim_bed                   -> :Bed  + :inWard       (rdfs:label)
  dim_patient               -> :Patient             (rdfs:label)
  fct_admission             -> :Admission + links + timestamps + status
  fct_admission status=current -> patient :occupiesBed bed   (live occupancy)

Then it verifies the triple counts in Fuseki against the mart row counts.
"""
from __future__ import annotations

import os
import re
import sys

import duckdb
import requests
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

HOSP = Namespace("http://example.org/hospital#")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DUCKDB_PATH = os.environ.get("M1_DUCKDB", os.path.join(HERE, "hospital_ingest", "hospital.duckdb"))
ENDPOINT = os.environ.get("FUSEKI_ENDPOINT", "http://localhost:3030/hospital")
ONTOLOGY_FILES = [
    os.path.join(REPO, "m0-ontology", "ontology", "hospital-ontology.ttl"),
    os.path.join(HERE, "ontology", "hospital-admissions.ttl"),
]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def ward_uri(name: str) -> URIRef:
    s = slug(name)
    return HOSP[s if s.startswith("ward") else f"ward-{s}"]


def bed_uri(code: str) -> URIRef:
    return HOSP[f"bed-{slug(code)}"]


def patient_uri(pid: str) -> URIRef:
    return HOSP[f"pat-{slug(pid)}"]


def admission_uri(aid: str) -> URIRef:
    return HOSP[slug(aid)]


def build_graph() -> tuple[Graph, dict]:
    if not os.path.exists(DUCKDB_PATH):
        sys.exit(f"DuckDB not found at {DUCKDB_PATH}. Run `dbt run` first (see run.sh).")

    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    beds = con.execute("select bed_code, ward_name from dim_bed").fetchall()
    patients = con.execute("select patient_id, patient_name from dim_patient").fetchall()
    admissions = con.execute(
        "select admission_id, patient_id, bed_code, admitted_at, discharged_at, status "
        "from fct_admission"
    ).fetchall()
    con.close()

    g = Graph()
    g.bind("", HOSP)
    for f in ONTOLOGY_FILES:
        g.parse(f, format="turtle")

    # Wards (distinct, derived from beds)
    wards = {ward for _, ward in beds}
    for ward in sorted(wards):
        w = ward_uri(ward)
        g.add((w, RDF.type, HOSP.Ward))
        g.add((w, RDFS.label, Literal(ward)))

    # Beds
    for code, ward in beds:
        b = bed_uri(code)
        g.add((b, RDF.type, HOSP.Bed))
        g.add((b, RDFS.label, Literal(code)))
        g.add((b, HOSP.inWard, ward_uri(ward)))

    # Patients
    for pid, pname in patients:
        p = patient_uri(pid)
        g.add((p, RDF.type, HOSP.Patient))
        g.add((p, RDFS.label, Literal(pname)))

    # Admissions (+ live occupancy for current ones)
    n_current = 0
    for aid, pid, code, admitted_at, discharged_at, status in admissions:
        a = admission_uri(aid)
        g.add((a, RDF.type, HOSP.Admission))
        g.add((a, HOSP.admissionPatient, patient_uri(pid)))
        g.add((a, HOSP.admissionBed, bed_uri(code)))
        g.add((a, HOSP.admittedAt, Literal(admitted_at.isoformat(), datatype=XSD.dateTime)))
        g.add((a, HOSP.admissionStatus, Literal(status)))
        if discharged_at is not None:
            g.add((a, HOSP.dischargedAt, Literal(discharged_at.isoformat(), datatype=XSD.dateTime)))
        if status == "current":
            g.add((patient_uri(pid), HOSP.occupiesBed, bed_uri(code)))
            n_current += 1

    counts = dict(wards=len(wards), beds=len(beds), patients=len(patients),
                  admissions=len(admissions), current=n_current, triples=len(g))
    return g, counts


def put_default_graph(turtle: str) -> None:
    # PUT replaces the default graph entirely -> idempotent re-loads.
    r = requests.put(f"{ENDPOINT}/data?default",
                     data=turtle.encode("utf-8"),
                     headers={"Content-Type": "text/turtle"}, timeout=120)
    r.raise_for_status()


def ask_count(query: str) -> int:
    r = requests.post(f"{ENDPOINT}/sparql", data={"query": query},
                      headers={"Accept": "application/sparql-results+json"}, timeout=60)
    r.raise_for_status()
    return int(r.json()["results"]["bindings"][0]["n"]["value"])


def verify(counts: dict) -> bool:
    q = lambda cls: ("PREFIX : <http://example.org/hospital#> "
                     f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s a :{cls} }}")
    checks = [
        ("Ward instances",      ask_count(q("Ward")),      counts["wards"]),
        ("Bed instances",       ask_count(q("Bed")),       counts["beds"]),
        ("Patient instances",   ask_count(q("Patient")),   counts["patients"]),
        ("Admission instances", ask_count(q("Admission")), counts["admissions"]),
        ("Current occupancy (occupiesBed)",
         ask_count("PREFIX : <http://example.org/hospital#> "
                   "SELECT (COUNT(*) AS ?n) WHERE { ?p :occupiesBed ?b }"),
         counts["current"]),
    ]
    total = ask_count("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")

    print("\nVerification — Fuseki triplestore vs dbt mart row counts")
    print("-" * 60)
    ok = True
    for label, got, expected in checks:
        mark = "OK " if got == expected else "FAIL"
        ok = ok and got == expected
        print(f"  [{mark}] {label:<34} fuseki={got:<6} expected={expected}")
    print(f"\n  Total triples in store: {total} (built graph: {counts['triples']})")
    ok = ok and total == counts["triples"]
    print("-" * 60)
    print("RESULT:", "ALL CHECKS PASSED ✅" if ok else "MISMATCH ❌")
    return ok


def main() -> None:
    try:
        requests.get(f"{ENDPOINT.rsplit('/', 1)[0]}/$/ping", timeout=5)
    except requests.RequestException:
        sys.exit(f"Fuseki not reachable at {ENDPOINT}. Start it: m0-ontology/serve.sh")

    print(f"Building triples from {DUCKDB_PATH} ...")
    g, counts = build_graph()
    print(f"  wards={counts['wards']} beds={counts['beds']} patients={counts['patients']} "
          f"admissions={counts['admissions']} current={counts['current']}")
    print(f"  -> {counts['triples']} triples (ontology + instances)")

    print(f"Replacing default graph in {ENDPOINT} ...")
    put_default_graph(g.serialize(format="turtle"))

    if not verify(counts):
        sys.exit(1)


if __name__ == "__main__":
    main()
