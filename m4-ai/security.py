"""Security routing for the AI agent (reuses the Module 3 OPA policy).

The agent must respect permissions. Rather than *trusting the LLM* to scope its
own query (which a hallucination could bypass), we ENFORCE scoping on the data:

  * bed_manager  -> query runs against the full Fuseki dataset.
  * ward_nurse   -> we materialise a view graph containing ONLY their ward's
                    beds/patients/wards, and run the generated query against
                    that. The model literally cannot see other wards' triples.

So even a query that says "all beds" returns only the permitted rows.
"""
from __future__ import annotations

import os

import requests
from rdflib import Graph

OPA_URL = os.environ.get("OPA_URL", "http://127.0.0.1:8181/v1/data/hospital/authz/decision")
FUSEKI = os.environ.get("FUSEKI_ENDPOINT", "http://localhost:3030/hospital")
QUERY_URL = f"{FUSEKI}/sparql"

PREFIXES = """PREFIX :    <http://example.org/hospital#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def _lit(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def decide(user: str, ward: str = "") -> dict:
    """Ask OPA: may this user view beds, and scoped to which ward?"""
    try:
        r = requests.post(OPA_URL, json={"input": {
            "user": user, "action": "view_beds", "ward": ward or ""}}, timeout=5)
        r.raise_for_status()
        return r.json().get("result", {"allow": False, "ward_filter": ""})
    except requests.RequestException:
        return {"allow": False, "ward_filter": ""}


def _scoped_view(ward_label: str) -> Graph:
    """Materialise a view graph for one ward via CONSTRUCT against Fuseki."""
    construct = PREFIXES + f"""
    CONSTRUCT {{
        ?ward a :Ward ; rdfs:label ?wl .
        ?bed  a :Bed  ; rdfs:label ?bl ; :inWard ?ward .
        ?pat  a :Patient ; rdfs:label ?pl ; :occupiesBed ?bed .
    }} WHERE {{
        ?ward rdfs:label {_lit(ward_label)} ; rdfs:label ?wl .
        ?bed a :Bed ; :inWard ?ward ; rdfs:label ?bl .
        OPTIONAL {{ ?pat :occupiesBed ?bed ; rdfs:label ?pl }}
    }}"""
    r = requests.post(QUERY_URL, data={"query": construct},
                      headers={"Accept": "text/turtle"}, timeout=30)
    r.raise_for_status()
    return Graph().parse(data=r.text, format="turtle")


def _fuseki_select(sparql: str) -> tuple[list[str], list[list[str]]]:
    r = requests.post(QUERY_URL, data={"query": sparql},
                      headers={"Accept": "application/sparql-results+json"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    cols = data["head"]["vars"]
    rows = [[b.get(c, {}).get("value", "") for c in cols] for b in data["results"]["bindings"]]
    return cols, rows


def run_scoped(sparql: str, decision: dict) -> tuple[list[str], list[list[str]]]:
    """Execute the generated query within the user's permission scope."""
    ward = decision.get("ward_filter") or ""
    if not ward:                       # bed_manager: full dataset
        return _fuseki_select(sparql)
    g = _scoped_view(ward)             # ward_nurse: only their ward's triples
    res = g.query(sparql)
    cols = [str(v) for v in res.vars] if res.vars else []
    rows = [[str(row[v]) if row[v] is not None else "" for v in res.vars] for row in res]
    return cols, rows
