#!/usr/bin/env python3
"""Verify Module 3 dynamic security: one request, different roles, different
result sets — enforced by the external OPA policy, not the app.

Prereqs: OPA on :8181 (run_opa.sh) and the M2 API on :8000 (m2-actions/run.sh).
"""
from __future__ import annotations

import sys

import requests

API = "http://127.0.0.1:8000"
OPA = "http://127.0.0.1:8181/v1/data/hospital/authz/decision"
passed = failed = 0


def check(name: str, ok: bool, extra: str = "") -> None:
    global passed, failed
    passed, failed = passed + ok, failed + (not ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {extra}" if extra else ""))


def secure_beds(user: str, ward: str | None = None):
    params = {"ward": ward} if ward else {}
    return requests.get(f"{API}/secure/beds", headers={"X-User": user}, params=params, timeout=10)


def wards_in(resp) -> set[str]:
    return {b["ward"] for b in resp.json()["beds"]}


def main() -> None:
    # Sanity: OPA reachable and returns the expected shape.
    d = requests.post(OPA, json={"input": {"user": "nurse_alice", "action": "view_beds", "ward": ""}},
                      timeout=5).json().get("result", {})
    check("OPA decision endpoint reachable", bool(d), str(d))

    print("\nSame request `GET /secure/beds`, three identities:")
    mgr = secure_beds("manager_carol")
    alice = secure_beds("nurse_alice")
    bob = secure_beds("nurse_bob")
    for r in (mgr, alice, bob):
        check(f"  {r.json()['user']} allowed (200)", r.status_code == 200, f"status={r.status_code}")

    mgr_count = mgr.json()["count"]
    print()
    check("bed_manager sees ALL wards", wards_in(mgr) == {"ICU", "Ward A", "Ward B", "Ward C"},
          f"{mgr_count} beds across {sorted(wards_in(mgr))}")
    check("nurse_alice sees ONLY Ward A", wards_in(alice) == {"Ward A"},
          f"{alice.json()['count']} beds, scope={alice.json()['role_scope']}")
    check("nurse_bob sees ONLY Ward B", wards_in(bob) == {"Ward B"},
          f"{bob.json()['count']} beds, scope={bob.json()['role_scope']}")

    print("\nThe core deliverable — one request, different result sets:")
    check("manager and nurse_alice get DIFFERENT results",
          mgr.json()["count"] != alice.json()["count"] and wards_in(mgr) != wards_in(alice))
    check("nurse_alice and nurse_bob get DIFFERENT results",
          wards_in(alice) != wards_in(bob))

    print("\nDeny paths:")
    denied = secure_beds("nurse_alice", ward="ICU")
    check("nurse_alice requesting another ward (ICU) is DENIED (403)", denied.status_code == 403,
          f"status={denied.status_code}")
    intruder = secure_beds("intruder_mallory")
    check("unknown user is DENIED (403)", intruder.status_code == 403, f"status={intruder.status_code}")

    print(f"\n{'='*52}\nRESULT: {passed} passed, {failed} failed",
          "✅" if failed == 0 else "❌")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
