"""Thin HTTP wrapper around the M4 agent, so the M5 app can call it.

Run from the m4-ai/ folder:  uvicorn server:app --port 8002
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from agent import ask as agent_ask

app = FastAPI(title="Hospital AI Agent (M4)")


class AskRequest(BaseModel):
    question: str
    user: str = "manager_carol"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    res = agent_ask(req.question, req.user)
    # Return a UI-friendly subset.
    return {
        "allowed": res.get("allowed", False),
        "scope": res.get("scope"),
        "answer": res.get("answer"),
        "sparql": res.get("sparql"),
        "row_count": res.get("row_count"),
    }
