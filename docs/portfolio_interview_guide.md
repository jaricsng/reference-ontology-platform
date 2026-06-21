# Portfolio & Interview Guide: The Reference Ontology Platform

**A companion to the *Building a Reference Ontology Platform* lab**

You've built an end-to-end reference implementation of an ontology-driven operational data platform. This guide helps you talk about it honestly and well — on a CV, in a portfolio, and in a technical interview — in a way that builds credibility rather than risking it.

The core principle runs through everything below: **precise, slightly modest framing beats impressive-sounding overstatement every time.** An interviewer who hears "I built a production platform" will probe for two minutes, find the seams, and lose trust. A candidate who says "I built a learning prototype to understand the architecture, and here's exactly what production would need" demonstrates *more* senior judgment. For a career-switcher, that gap-awareness is the most valuable thing you can show.

> **How to use this guide:** The claims and interview answers below are *models to adapt, not scripts to memorise.* Recited verbatim they will sound rehearsed — and an interviewer can tell. Work through the lab modules first, then rewrite each answer in your own voice using the specifics of what *you* actually built, hit, and fixed. The genuine details from your own build are always more convincing than any template.

---

## What you genuinely built

A working prototype that touches every layer of an operational data platform, on synthetic data, at laptop scale:

- A **formal domain ontology** (OWL/RDF) with a reasoner enforcing model constraints
- A **data ingestion + transformation pipeline** (dbt + DuckDB) with visible lineage
- **Validated write-actions** — the guarded "validate → write → log" pattern (SHACL + an API service)
- **Policy-based access control** that scopes results per user role (OPA)
- An **AI query layer** that translates natural language into ontology queries, grounded in real data (local LLM + LangChain)
- **GitOps deployment** on Kubernetes (k3d + Argo CD)

That breadth — modelling through deployment, integrated around one coherent domain — is the real achievement. You understand how the pieces fit, not just one of them in isolation.

---

## What it is *not* — and why saying so helps you

Be ready to state this plainly. It is **not** production-grade, not scalable as built, not concurrency-safe, not security-hardened, not integration-complete, and not operated (no monitoring, HA, or backup). It runs on synthetic data and a single instance.

Naming these is not a weakness to hide — it is *evidence of judgment*. The ability to draw the boundary precisely is exactly what distinguishes an engineer from a tutorial-follower, and it's a large part of what an employer in this space is screening for. Underclaiming with precision is a strength.

---

## Defensible claims (use these)

**On a CV / LinkedIn:**

> *Self-directed reference implementation — built an end-to-end prototype of an ontology-driven operational data platform: domain modelling in OWL/RDF, data ingestion with dbt, validated write-actions, policy-based access control, an LLM query layer, and GitOps deployment on Kubernetes. A learning artifact on synthetic data, built to understand platform architecture and build-vs-buy trade-offs.*

**In conversation:**

> *"I wanted to understand how ontology-driven operational platforms actually work, so I built a small one end-to-end. It runs on synthetic data — it's a learning prototype — but it covers the whole stack, and building it taught me where the genuinely hard problems are and what you'd need to add for production."*

**Phrases that are honest and strong:**
- "reference implementation" / "working prototype"
- "end-to-end, on synthetic data"
- "built to understand the architecture and trade-offs"
- "I can walk you through what production would require"

**Phrases to avoid (they invite a takedown):**
- ✗ "I built a Foundry alternative" / "I built [vendor] from scratch"
- ✗ "production-ready" / "enterprise-grade" / "scalable platform"
- ✗ anything implying real users, real data, or operational deployment

---

## Interview defence: likely questions & strong answers

These are the questions a competent interviewer will ask. The answers below are honest *and* credibility-building — practise them in your own words.

**Q: "Is this production-ready?"**
> "No, and deliberately not — it's a learning prototype on synthetic data at single-instance scale. It demonstrates every layer of the architecture, but production would need real scale, concurrency control, hardened security, live data integration, and full operations. I built it to understand the whole shape of the system and the trade-offs, and I'm happy to walk through exactly what each of those gaps would take."

**Q: "What was the hardest or most surprising part?"**
> "The ontology layer. I learned that a formal model in OWL describes valid states but can't *enforce* them on writes — OWL is open-world, so 'not stated' means 'unknown', not 'forbidden'. To get operational guarantees I had to add SHACL validation in front of every write. That gap between a descriptive model and an operational one was the most genuinely non-obvious lesson." *(This answer demonstrates real understanding — it's specific and not something you'd say from a tutorial alone.)*

**Q: "How would you scale this?"**
> "Three main moves. The compute layer is already portable — in the capstone I swapped DuckDB for Spark with identical output, so that scales horizontally. The triplestore is the bottleneck: a single instance handles thousands of objects, so I'd move to a clustered store and add a search index for operational query patterns. And the single API instance would need horizontal scaling behind a load balancer with proper concurrency control on the write-actions."

**Q: "Why an ontology / graph model instead of just a relational database?"**
> "For operational platforms the value is modelling rich relationships and reasoning over them — 'which patients in occupied beds in this ward are awaiting transfer' is a graph traversal that's awkward in SQL. The formal model also gives you consistency checking via a reasoner. That said, I'd choose a property graph over OWL when fast traversal matters more than formal inference — they're different tools."

**Q: "How does the AI layer avoid hallucinating answers?"**
> "It's grounded — the LLM doesn't answer from memory, it generates a query against the ontology and the answer comes from real data. The main failure mode is the model inventing a property name that isn't in the schema, so I provide the schema as context and validate the generated query before running it. And the query goes through the same access-control filter, so the agent can't bypass permissions."

**Q: "What would you do differently / what are the weaknesses?"**
> "The action layer is hand-rolled per action — that wouldn't scale to hundreds of action types; I'd want a generalised framework. The security is illustrative rather than hardened. And I'd add observability from the start next time — I bolted deployment on at the end, and in hindsight monitoring should be part of each service as you build it."

---

## How to demo it (if asked to walk through)

Keep it to the story, not the code tour. A strong 5-minute walk-through:

1. **One sentence of framing** — "This is a learning prototype of an ontology-driven platform on synthetic hospital bed-flow data."
2. **Show the model** — the ontology and one SPARQL query ("free beds in a ward").
3. **Show an action** — admit a patient through the UI; show it's *blocked* when the bed is occupied. This is the most impressive moment — it shows guarded operations, not just display.
4. **Show the AI query** — ask a question in natural language, show it resolve against real data.
5. **Close on the gap** — "It's deployed via GitOps on local Kubernetes; it's not production-grade, and here's what I'd add next." End on judgment, not a claim.

---

## Mapping your work to job-description language

When a role description lists skills, here's how your lab experience maps — claim these only as far as the prototype supports, framed as "built a prototype using…":

| Job-ad skill | What in the lab supports it |
|---|---|
| Data modelling / ontologies / knowledge graphs | Module 0 — OWL/RDF modelling, reasoning, SPARQL |
| Data pipelines / ELT / transformation | Module 1 — dbt + DuckDB with lineage |
| Data quality / validation | Module 2 — SHACL shape validation |
| API / backend services | Module 2 — FastAPI action service |
| Access control / authorization | Module 3 — OPA policy enforcement |
| LLM / RAG / AI integration | Module 4 — grounded NL-to-query agent |
| Frontend / dashboards | Module 5 — operational app |
| Kubernetes / containers / GitOps / DevOps | Module 6 — k3d + Argo CD |
| Systems thinking / architecture | The whole build + capstone gap analysis |

---

## The one-line summary to internalise

> *"I built a working, end-to-end prototype of an ontology-driven data platform on synthetic data — enough to understand the architecture deeply and to speak precisely about what production would require. It's a learning artifact, and that gap-awareness is part of what I learned."*

That sentence is honest, demonstrates breadth, and signals exactly the judgment the role needs. Lead with it.
