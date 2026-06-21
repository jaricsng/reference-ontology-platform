#!/usr/bin/env python3
"""End-to-end verification of the Module 2 action guard.

Drives the live API only (no direct DB access) and checks:
  A. a valid admit to a free bed succeeds and updates the graph
  B. admitting to an occupied bed is REJECTED (409) before any write
  C. admitting a patient who already has a bed is REJECTED (409)
  D. discharge frees the bed (so the test is repeatable)
  E. the audit log recorded who/what/when for each attempt
"""
from __future__ import annotations

import sys

import requests

API = "http://127.0.0.1:8000"
passed = failed = 0


def check(name: str, ok: bool, extra: str = "") -> None:
    global passed, failed
    mark = "PASS" if ok else "FAIL"
    passed, failed = passed + ok, failed + (not ok)
    print(f"  [{mark}] {name}" + (f"  — {extra}" if extra else ""))


def get_beds():
    return requests.get(f"{API}/beds", timeout=10).json()["beds"]


def main() -> None:
    if not requests.get(f"{API}/health", timeout=5).ok:
        sys.exit("API /health not OK — is the server running and Fuseki up?")

    beds = get_beds()
    free = [b for b in beds if not b["occupied"]]
    occ = [b for b in beds if b["occupied"]]
    if len(free) < 2 or not occ:
        sys.exit("Need at least 2 free beds and 1 occupied bed in the data.")
    free1, free2 = free[0]["bed_code"], free[1]["bed_code"]
    occ_patient = occ[0]["occupant_id"]
    print(f"Using free beds {free1}, {free2}; existing occupant '{occ_patient}'.\n")

    # Clean slate for our test patient's target bed.
    requests.post(f"{API}/discharge", json={"bed_code": free1, "actor": "test_setup"})

    print("A. valid admit to a free bed")
    r = requests.post(f"{API}/admit", json={"patient_id": "SYN-PTEST1", "bed_code": free1,
                                            "actor": "nurse_jane", "patient_name": "SYN Test Patient One"})
    check("returns 200", r.status_code == 200, f"status={r.status_code}")
    after = {b["bed_code"]: b for b in get_beds()}
    check(f"bed {free1} now occupied by syn-ptest1",
          after[free1]["occupied"] and after[free1]["occupant_id"] == "syn-ptest1")

    print("\nB. admit to an already-occupied bed (must be rejected, no write)")
    r = requests.post(f"{API}/admit", json={"patient_id": "SYN-PTEST2", "bed_code": free1,
                                            "actor": "nurse_jane"})
    check("returns 409", r.status_code == 409, f"status={r.status_code}")
    check("reason mentions occupied bed",
          "already occupied" in str(r.json()).lower(), str(r.json().get("detail", {}).get("reasons")))
    still = {b["bed_code"]: b for b in get_beds()}
    check("occupant unchanged (no write happened)", still[free1]["occupant_id"] == "syn-ptest1")

    print("\nC. admit a patient who already occupies a bed (must be rejected)")
    r = requests.post(f"{API}/admit", json={"patient_id": occ_patient, "bed_code": free2,
                                            "actor": "nurse_jane"})
    check("returns 409", r.status_code == 409, f"status={r.status_code}")
    check("reason mentions more than one bed",
          "more than one bed" in str(r.json()).lower())

    print("\nD. discharge frees the bed")
    r = requests.post(f"{API}/discharge", json={"bed_code": free1, "actor": "nurse_jane"})
    check("returns 200", r.status_code == 200, f"status={r.status_code}")
    freed = {b["bed_code"]: b for b in get_beds()}
    check(f"bed {free1} free again", not freed[free1]["occupied"])

    print("\nE. audit log records who/what/when")
    entries = requests.get(f"{API}/audit", params={"n": 20}, timeout=10).json()["entries"]
    outcomes = [(e["actor"], e["action"], e["outcome"]) for e in entries]
    check("a success admit is logged", ("nurse_jane", "admit", "success") in outcomes)
    check("a rejected admit is logged", any(a == "admit" and o == "rejected" for _, a, o in outcomes))
    check("entries have timestamps", all(e.get("ts") for e in entries))
    print("\n  last 4 audit entries:")
    for e in entries[-4:]:
        print(f"    {e['ts']}  {e['actor']:<11} {e['action']:<10} {e['outcome']:<9} "
              f"patient={e['patient']} bed={e['bed']}  {e['detail']}")

    print(f"\n{'='*50}\nRESULT: {passed} passed, {failed} failed",
          "✅" if failed == 0 else "❌")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
