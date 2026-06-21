#!/usr/bin/env python3
"""Verify Module 4: the agent generates valid SPARQL, answers correctly against
ground truth, and respects Module 3 security (no permission bypass).

Prereqs: Ollama (model pulled), Fuseki (M1 data), OPA — all running.
Note: each question is a real local-LLM call, so this takes a couple of minutes.
"""
from __future__ import annotations

import sys

import requests

from agent import ask

FUSEKI = "http://localhost:3030/hospital/sparql"
passed = failed = 0


def check(name, ok, extra=""):
    global passed, failed
    passed, failed = passed + ok, failed + (not ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {extra}" if extra else ""))


def truth(sparql: str) -> int:
    r = requests.post(FUSEKI, data={"query": sparql},
                      headers={"Accept": "application/sparql-results+json"}, timeout=30)
    r.raise_for_status()
    b = r.json()["results"]["bindings"]
    return int(list(b[0].values())[0]["value"]) if b else 0


def num(res) -> int:
    """Derive a number from the agent's executed rows (COUNT cell or row count)."""
    rows = res.get("rows") or []
    if len(rows) == 1 and len(rows[0]) == 1:
        try:
            return int(float(rows[0][0]))
        except ValueError:
            pass
    return res.get("row_count", 0)


P = "PREFIX : <http://example.org/hospital#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "


def main():
    print("== A. Grounded accuracy (as bed_manager, full data) ==")
    cases = [
        ("How many beds are free in the ICU ward?",
         P + 'SELECT (COUNT(?b) AS ?n) WHERE { ?b a :Bed ; :inWard ?w . ?w rdfs:label "ICU" . FILTER NOT EXISTS { ?p :occupiesBed ?b } }'),
        ("How many beds are there in Ward B?",
         P + 'SELECT (COUNT(?b) AS ?n) WHERE { ?b a :Bed ; :inWard ?w . ?w rdfs:label "Ward B" }'),
        ("How many patients are currently occupying a bed in total?",
         P + 'SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p :occupiesBed ?b }'),
    ]
    for q, gt in cases:
        res = ask(q, "manager_carol")
        valid = "error" not in res and res.get("row_count") is not None
        t = truth(gt)
        check(f"{q[:46]:46} -> {num(res)} (truth {t})", valid and num(res) == t)

    print("\n== B. Security: same question, scoped per role (no bypass) ==")
    q_total = "How many beds are there in total?"
    mgr = ask(q_total, "manager_carol")
    alice = ask(q_total, "nurse_alice")
    bob = ask(q_total, "nurse_bob")
    check(f"bed_manager total beds = 68", num(mgr) == 68, f"got {num(mgr)}")
    check(f"nurse_alice sees only her ward (20)", num(alice) == 20, f"got {num(alice)}")
    check(f"nurse_bob sees only his ward (20)", num(bob) == 20, f"got {num(bob)}")
    check("same question -> manager and nurse get different totals", num(mgr) != num(alice))

    print("\n== C. A ward nurse cannot reach another ward's data ==")
    icu_as_alice = ask("List all beds in the ICU ward.", "nurse_alice")
    icu_as_mgr = ask("List all beds in the ICU ward.", "manager_carol")
    check("nurse_alice gets NO ICU beds (scoped out)", num(icu_as_alice) == 0, f"rows={num(icu_as_alice)}")
    check("manager_carol can see ICU beds", num(icu_as_mgr) > 0, f"rows={num(icu_as_mgr)}")

    print("\n== D. Unknown user denied ==")
    intruder = ask("How many beds are free?", "intruder_mallory")
    check("unknown user denied", intruder.get("allowed") is False)

    print("\n  sample answer (manager, ICU free beds):")
    print("   ", ask("How many beds are free in the ICU?", "manager_carol")["answer"])

    print(f"\n{'='*54}\nRESULT: {passed} passed, {failed} failed",
          "✅" if failed == 0 else "❌")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
