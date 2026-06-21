"""Module 2 — Validation & Actions (kinetic layer).

A guarded `admit` state transition: validate the proposed change with SHACL,
and ONLY if it conforms, write it to the triplestore and append an audit entry.
Invalid actions (occupied bed, patient already in a bed) are rejected before
any write.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import audit
from .shacl_check import validate_graph
from .sparql import (HOSP, ask, bed_uri, current_occupancy_graph,
                     patient_id_from_uri, patient_uri, ping, select, update)

app = FastAPI(title="Hospital Action API (M2)",
              description="Guarded admit/discharge actions with SHACL validation + audit log.")


class AdmitRequest(BaseModel):
    patient_id: str = Field(..., examples=["SYN-PTEST1"])
    bed_code: str = Field(..., examples=["A4"])
    actor: str = Field(..., description="Who is performing the action (for the audit log).",
                       examples=["nurse_jane"])
    patient_name: str | None = Field(None, examples=["SYN Test Patient One"])


class DischargeRequest(BaseModel):
    bed_code: str = Field(..., examples=["A4"])
    actor: str = Field(..., examples=["nurse_jane"])


@app.get("/health")
def health():
    if not ping():
        raise HTTPException(503, "Fuseki not reachable")
    return {"status": "ok", "fuseki": "up"}


@app.get("/beds")
def beds(ward: str | None = None):
    """Current bed occupancy. (Module 3 will scope this per role.)"""
    # `ward` is untrusted input — escape it as a SPARQL literal (see _q) to
    # avoid query injection.
    flt = 'FILTER(?ward = ?wardFilter)' if ward else ""
    binding = f'VALUES ?wardFilter {{ {_q(ward)} }}' if ward else ""
    rows = select(f"""
        SELECT ?bedCode ?ward ?occupantUri ?occupantName WHERE {{
            {binding}
            ?bed a :Bed ; rdfs:label ?bedCode ; :inWard ?w .
            ?w rdfs:label ?ward .
            OPTIONAL {{ ?occupantUri :occupiesBed ?bed . OPTIONAL {{ ?occupantUri rdfs:label ?occupantName }} }}
            {flt}
        }} ORDER BY ?ward ?bedCode""")
    out = []
    for r in rows:
        occ = "occupantUri" in r
        out.append({
            "bed_code": r["bedCode"]["value"],
            "ward": r["ward"]["value"],
            "occupied": occ,
            "occupant_id": patient_id_from_uri(r["occupantUri"]["value"]) if occ else None,
            "occupant_name": r["occupantName"]["value"] if "occupantName" in r else None,
        })
    return {"count": len(out), "beds": out}


@app.post("/admit")
def admit(req: AdmitRequest):
    bed = bed_uri(req.bed_code)
    pat = patient_uri(req.patient_id)
    name = req.patient_name or req.patient_id

    # Referential check: the bed must exist (app-level guard, not a business rule).
    if not ask(f"ASK {{ <{bed}> a :Bed }}"):
        audit.record(req.actor, "admit", req.patient_id, req.bed_code, "rejected",
                     "bed does not exist")
        raise HTTPException(404, f"Bed '{req.bed_code}' does not exist")

    # --- VALIDATE: build the proposed graph and run SHACL ---
    proposed = current_occupancy_graph()
    proposed.add((pat, HOSP.occupiesBed, bed))
    conforms, messages = validate_graph(proposed)
    if not conforms:
        audit.record(req.actor, "admit", req.patient_id, req.bed_code, "rejected",
                     "; ".join(messages))
        raise HTTPException(status_code=409,
                            detail={"error": "admit rejected — violates a business rule",
                                    "reasons": messages})

    # --- WRITE: commit occupancy + a new Admission record ---
    adm = HOSP[f"adm-live-{uuid4().hex[:10]}"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    update(f"""
        INSERT DATA {{
            <{pat}> a :Patient ; rdfs:label {_q(name)} .
            <{pat}> :occupiesBed <{bed}> .
            <{adm}> a :Admission ;
                    :admissionPatient <{pat}> ;
                    :admissionBed <{bed}> ;
                    :admittedAt "{now}"^^xsd:dateTime ;
                    :admissionStatus "current" .
        }}""")

    # --- LOG ---
    entry = audit.record(req.actor, "admit", req.patient_id, req.bed_code, "success",
                         f"admission {adm.split('#')[-1]}")
    return {"result": "admitted", "patient_id": req.patient_id, "bed_code": req.bed_code,
            "admission": adm.split("#")[-1], "audit": entry}


@app.post("/discharge")
def discharge(req: DischargeRequest):
    bed = bed_uri(req.bed_code)
    occ = select(f"SELECT ?p WHERE {{ ?p :occupiesBed <{bed}> }}")
    if not occ:
        raise HTTPException(409, f"Bed '{req.bed_code}' is not currently occupied")
    patient_id = patient_id_from_uri(occ[0]["p"]["value"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    update(f"DELETE WHERE {{ ?p :occupiesBed <{bed}> }}")
    update(f"""
        DELETE {{ ?a :admissionStatus "current" }}
        INSERT {{ ?a :admissionStatus "discharged" ; :dischargedAt "{now}"^^xsd:dateTime }}
        WHERE  {{ ?a :admissionBed <{bed}> ; :admissionStatus "current" }}""")

    entry = audit.record(req.actor, "discharge", patient_id, req.bed_code, "success", "bed freed")
    return {"result": "discharged", "patient_id": patient_id, "bed_code": req.bed_code, "audit": entry}


@app.get("/audit")
def audit_tail(n: int = 10):
    return {"entries": audit.tail(n)}


def _q(s: str) -> str:
    """Quote/escape a string as a SPARQL string literal (injection-safe)."""
    s = (s.replace("\\", "\\\\").replace('"', '\\"')
          .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
    return f'"{s}"'
