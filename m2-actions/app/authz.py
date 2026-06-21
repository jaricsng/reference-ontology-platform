"""OPA authorization client (Module 3 integration).

The application does not contain any access rules — it asks OPA for a decision.
OPA returns {allow, ward_filter}; the API enforces it by injecting the ward
filter into the bed query. Policy + data live in m3-security/, outside this app.
"""
from __future__ import annotations

import os

import requests

OPA_URL = os.environ.get(
    "OPA_URL", "http://127.0.0.1:8181/v1/data/hospital/authz/decision")

DENY = {"allow": False, "ward_filter": ""}


def decide(user: str, ward: str = "") -> dict:
    """Ask OPA whether `user` may view beds, and scoped to which ward."""
    try:
        r = requests.post(OPA_URL, json={"input": {
            "user": user, "action": "view_beds", "ward": ward or ""}}, timeout=5)
        r.raise_for_status()
    except requests.RequestException:
        return DENY
    return r.json().get("result", DENY)
