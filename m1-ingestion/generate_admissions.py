#!/usr/bin/env python3
"""Generate a synthetic hospital admissions CSV for the Module 1 pipeline.

SYNTHETIC DATA ONLY — obviously-fake patient identities, never real PHI.

Produces ~10,000 clean admission events plus a handful of deliberately *dirty*
rows (duplicates, blank ids, whitespace/case noise) so the dbt staging layer
has real cleaning work to do. Deterministic via a fixed seed.

Invariant we preserve: at most one *current* (un-discharged) admission per bed,
and each current occupant is a distinct patient — so the data respects the M0
"a bed holds at most one patient" rule when loaded.
"""
from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta

SEED = 42
N_CLEAN = 10_000          # clean, unique admissions
OCCUPANCY_RATE = 0.66     # fraction of beds occupied "now"
WINDOW_START = datetime(2025, 6, 1)
WINDOW_END = datetime(2026, 6, 21)   # "now" for this synthetic world

# Fixed ward / bed reference structure (one ward per bed).
WARDS = {
    "ICU":    [f"ICU-{i}" for i in range(1, 13)],   # 12 beds
    "Ward A": [f"A{i}" for i in range(1, 21)],      # 20 beds
    "Ward B": [f"B{i}" for i in range(1, 21)],      # 20 beds
    "Ward C": [f"C{i}" for i in range(1, 17)],      # 16 beds
}
BEDS = [(code, ward) for ward, codes in WARDS.items() for code in codes]  # 68 beds

OUT = os.path.join(os.path.dirname(__file__), "data", "raw", "admissions.csv")


def rand_dt(start: datetime, end: datetime) -> datetime:
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))


def main() -> None:
    random.seed(SEED)

    # Patient pool — obviously synthetic identities.
    n_patients = 2_000
    patients = [f"SYN-P{n:05d}" for n in range(1, n_patients + 1)]

    rows: list[dict] = []

    # --- Current occupancy: distinct beds, distinct patients, no discharge ---
    n_current = int(len(BEDS) * OCCUPANCY_RATE)
    occupied_beds = random.sample(BEDS, n_current)
    current_patients = random.sample(patients, n_current)
    for (bed_code, ward), patient in zip(occupied_beds, current_patients):
        admit = rand_dt(WINDOW_END - timedelta(days=14), WINDOW_END - timedelta(hours=1))
        rows.append(dict(patient_id=patient, ward_name=ward, bed_code=bed_code,
                         admit_ts=admit, discharge_ts=None))

    # --- Historical (discharged) admissions to fill out to N_CLEAN ---
    while len(rows) < N_CLEAN:
        patient = random.choice(patients)
        bed_code, ward = random.choice(BEDS)
        admit = rand_dt(WINDOW_START, WINDOW_END - timedelta(days=1))
        los = timedelta(hours=random.randint(6, 240))
        discharge = min(admit + los, WINDOW_END - timedelta(hours=1))
        rows.append(dict(patient_id=patient, ward_name=ward, bed_code=bed_code,
                         admit_ts=admit, discharge_ts=discharge))

    # Shuffle then assign sequential admission ids (so "current" rows aren't clustered).
    random.shuffle(rows)
    for i, r in enumerate(rows, start=1):
        r["admission_id"] = f"ADM-{i:06d}"
        r["patient_name"] = f"SYN Patient {r['patient_id'].split('-')[1]}"

    # --- Inject dirtiness the staging layer must handle ---
    # (a) whitespace / lower-case noise, in place, on ~20% of rows
    for r in random.sample(rows, k=int(len(rows) * 0.20)):
        r["ward_name"] = f"  {r['ward_name']}  "
        r["bed_code"] = r["bed_code"].lower()

    dirty: list[dict] = []
    # (b) exact duplicate rows (same admission_id) -> staging must dedupe
    for r in random.sample(rows, k=60):
        dirty.append(dict(r))
    # (c) rows with blank required fields -> staging must drop
    for _ in range(10):
        bed_code, ward = random.choice(BEDS)
        dirty.append(dict(admission_id="", patient_id="SYN-P00001", patient_name="SYN Patient 00001",
                          ward_name=ward, bed_code=bed_code,
                          admit_ts=rand_dt(WINDOW_START, WINDOW_END), discharge_ts=None))
    for _ in range(10):
        bed_code, ward = random.choice(BEDS)
        dirty.append(dict(admission_id=f"ADM-BAD{random.randint(1,9999)}", patient_id="",
                          patient_name="", ward_name=ward, bed_code=bed_code,
                          admit_ts=rand_dt(WINDOW_START, WINDOW_END), discharge_ts=None))

    all_rows = rows + dirty
    random.shuffle(all_rows)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fields = ["admission_id", "patient_id", "patient_name", "ward_name",
              "bed_code", "admit_ts", "discharge_ts"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow({
                "admission_id": r["admission_id"],
                "patient_id": r["patient_id"],
                "patient_name": r["patient_name"],
                "ward_name": r["ward_name"],
                "bed_code": r["bed_code"],
                "admit_ts": r["admit_ts"].isoformat() if r["admit_ts"] else "",
                "discharge_ts": r["discharge_ts"].isoformat() if r["discharge_ts"] else "",
            })

    print(f"Wrote {len(all_rows)} raw rows to {OUT}")
    print(f"  clean unique admissions : {len(rows)}")
    print(f"  current occupancy (beds): {n_current} of {len(BEDS)}")
    print(f"  dirty rows injected     : {len(dirty)} (dupes + blanks)")


if __name__ == "__main__":
    main()
