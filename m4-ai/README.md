# M4 — AI Layer

A grounded Q&A agent: ask a question in plain English, the agent generates
SPARQL against the ontology, executes it **within your security scope**, and
summarises the rows in plain language. The point is not a chatbot — it is a
governed interface to the operational model, so answers come from real data, not
the model's memory.

**Synthetic data only — never real PHI. Local LLM only — nothing leaves the machine.**

## What this module contains

| Path | What it is |
|------|------------|
| `agent.py` | LangChain chain: question → SPARQL → execute → summarise (+ schema/prompt). |
| `security.py` | OPA decision + **enforced** ward scoping + query execution. |
| `ask.py` | CLI: `python ask.py --user nurse_alice "…"`. |
| `test_agent.py` | Verification: accuracy + security (no bypass). |

## How it works

```
question ─▶ [LLM: generate SPARQL]  one-shot, schema-grounded
         ─▶ [security.run_scoped]   bed_manager → full Fuseki
         │                          ward_nurse  → query runs on a ward-scoped view
         ─▶ [LLM: summarise rows]   plain-language answer from the result rows
```

**Grounding.** The generation prompt carries the ontology schema *and a worked
example* ("free beds in Ward A"). This matters: zero-shot, the model hallucinates
URIs (`:ICU`) and invalid syntax; one-shot, it reliably produces valid SPARQL.

**Security is enforced, not prompted.** We do not trust the LLM to scope its own
query. For a `ward_nurse` we materialise a view graph (via CONSTRUCT) containing
*only their ward's* beds/patients and run the generated query against that graph.
So even a query that says "all beds" can only return the permitted rows — there
is nothing else in the graph to find. The decision (allow + which ward) comes
from the Module 3 OPA policy.

## Prerequisites

- **Ollama** running with the model pulled:
  ```bash
  brew install ollama && ollama serve          # http://127.0.0.1:11434
  ollama pull qwen2.5-coder:7b                  # ~4.7GB; the lab's model
  ```
  Override with `OLLAMA_MODEL=…` (e.g. `llama3.2:3b` for faster, lower-quality).
- **Fuseki** with M1 data (`m0-ontology/serve.sh`) and **OPA** (`m3-security/run_opa.sh`).
- Repo venv deps: `.venv/bin/pip install -r m4-ai/requirements.txt`.

> On a CPU-only machine each question is a real local inference (~15–35s here).
> That is expected — the model runs entirely on your hardware.

## How to run

```bash
cd m4-ai
../.venv/bin/python ask.py --user manager_carol --show-sparql "How many beds are free in the ICU?"
../.venv/bin/python ask.py --user nurse_alice "How many beds are there in total?"
```

## How to verify

```bash
cd m4-ai && ../.venv/bin/python test_agent.py     # ~a few minutes (LLM calls)
```

Expected (10 checks, all pass):

```
A. Grounded accuracy (bed_manager)
   free beds in ICU -> 3 (truth 3); beds in Ward B -> 20; patients admitted -> 44
B. Security: "how many beds in total?"
   bed_manager -> 68;  nurse_alice -> 20 (Ward A only);  nurse_bob -> 20 (Ward B)
C. nurse_alice "list ICU beds" -> 0 rows (scoped out);  manager -> 12
D. unknown user -> denied
RESULT: 10 passed, 0 failed ✅
```

### Assessment criteria → evidence

- [x] **Valid SPARQL for ≥3 distinct questions** — section A (3 distinct, all execute).
- [x] **Answers correct vs ground truth** — each compared to a direct SPARQL count.
- [x] **Security filter applied (no bypass)** — sections B/C: a ward nurse's query,
  even when it asks for "all" or another ward, only ever sees their own ward,
  because it runs against a ward-scoped view; unknown users are denied.
- [x] **A failure mode + mitigation** — see below.

### Failure mode & mitigation

The main failure mode is a **hallucinated query**: a wrong property name, an
invented URI (`:ICU` instead of matching `rdfs:label "ICU"`), or invalid syntax.
Mitigations used here:

1. **Grounding** — the schema + a worked example in the prompt (the single biggest
   improvement; turns frequent zero-shot failures into reliable generation).
2. **Retry on error** — if the generated query fails to execute, the agent feeds
   the error back to the model once and regenerates (`agent.ask`).
3. **Scope as data, not trust** — wrong-but-valid queries still cannot leak data
   outside the user's permission, because the data isn't in the graph they query.

A code-tuned model (`qwen2.5-coder:7b`) was chosen over a general 3B precisely
because it produces more reliable SPARQL.
