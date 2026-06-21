"""SHACL validation of a proposed graph against the business-rule shapes."""
from __future__ import annotations

import os

from pyshacl import validate
from rdflib import Graph, Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")
SHAPES_FILE = os.path.join(os.path.dirname(__file__), "..", "shapes", "hospital-shapes.ttl")

# Load shapes once at import.
_shapes = Graph().parse(SHAPES_FILE, format="turtle")


def validate_graph(data_graph: Graph) -> tuple[bool, list[str]]:
    """Return (conforms, [violation messages])."""
    conforms, results_graph, _text = validate(
        data_graph,
        shacl_graph=_shapes,
        inference="none",
        abort_on_first=False,
        meta_shacl=False,
    )
    messages = sorted({str(m) for m in results_graph.objects(None, SH.resultMessage)})
    return conforms, messages
