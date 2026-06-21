"""Append-only audit log: who did what, to whom, when, and the outcome."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "audit")
LOG_PATH = os.path.join(AUDIT_DIR, "audit-log.jsonl")


def record(actor: str, action: str, patient: str, bed: str,
           outcome: str, detail: str = "") -> dict:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "patient": patient,
        "bed": bed,
        "outcome": outcome,   # "success" | "rejected" | "error"
        "detail": detail,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def tail(n: int = 10) -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-n:]]
