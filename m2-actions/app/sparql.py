"""Thin Fuseki client + URI helpers, shared by the action endpoints.

URI conventions match the M1 loader so actions write into the same graph:
  bed  -> :bed-<slug(code)>     patient -> :pat-<slug(id)>
"""
from __future__ import annotations

import os
import re

import requests
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS  # noqa: F401  (handy for callers)

HOSP = Namespace("http://example.org/hospital#")
ENDPOINT = os.environ.get("FUSEKI_ENDPOINT", "http://localhost:3030/hospital")
QUERY_URL = f"{ENDPOINT}/sparql"
UPDATE_URL = f"{ENDPOINT}/update"
PING_URL = f"{ENDPOINT.rsplit('/', 1)[0]}/$/ping"

PREFIXES = """PREFIX :    <http://example.org/hospital#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def bed_uri(code: str) -> URIRef:
    return HOSP[f"bed-{slug(code)}"]


def patient_uri(pid: str) -> URIRef:
    return HOSP[f"pat-{slug(pid)}"]


def patient_id_from_uri(uri: str) -> str:
    return uri.rsplit("#", 1)[-1].removeprefix("pat-")


def select(query: str) -> list[dict]:
    r = requests.post(QUERY_URL, data={"query": PREFIXES + query},
                      headers={"Accept": "application/sparql-results+json"}, timeout=30)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def ask(query: str) -> bool:
    r = requests.post(QUERY_URL, data={"query": PREFIXES + query},
                      headers={"Accept": "application/sparql-results+json"}, timeout=30)
    r.raise_for_status()
    return r.json()["boolean"]


def update(query: str) -> None:
    r = requests.post(UPDATE_URL, data={"update": PREFIXES + query}, timeout=30)
    r.raise_for_status()


def ping() -> bool:
    try:
        return requests.get(PING_URL, timeout=5).ok
    except requests.RequestException:
        return False


def current_occupancy_graph() -> Graph:
    """All `?p :occupiesBed ?b` triples as an rdflib graph, for SHACL validation."""
    g = Graph()
    for row in select("SELECT ?p ?b WHERE { ?p :occupiesBed ?b }"):
        g.add((URIRef(row["p"]["value"]), HOSP.occupiesBed, URIRef(row["b"]["value"])))
    return g
