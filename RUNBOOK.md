# RUNBOOK — run & test the whole platform

This is the operations guide for the **completed** solution: how to bring every
component up, use it, and run the full test suite in one place. The per-module
`README.md` files remain the source of truth for *why* each piece exists — this
runbook just orders their run/verify steps end to end.

> ⚠️ **Learning prototype on synthetic data. Local machine only.** No
> authentication, no real PHI. Do not expose any of these ports to an untrusted
> network. See the security note in the top-level [`README.md`](README.md).

There are two ways to run it:

- **[Path A — Local processes](#path-a--local-processes-m0m5)** (fastest; what
  you'll use day to day). Each component runs as a local process.
- **[Path B — Kubernetes via GitOps](#path-b--kubernetes-via-gitops-m6)** (M6).
  The same components as pods in a local k3d cluster, deployed by Argo CD.

---

## Prerequisites

| Tool | Needed for | Install |
|------|-----------|---------|
| Python 3.11+ | M1, M2, M3, M4 | python.org / pyenv |
| Node.js 18+ (with npm) | M5 (Next.js app) | nodejs.org |
| Java 17+ (JRE) | Fuseki | `brew install temurin` |
| Apache Jena Fuseki 6.1.0 | M0–M5 triplestore | downloaded binary (see [M0 README](m0-ontology/README.md)) → `tools/apache-jena-fuseki-6.1.0/` |
| Open Policy Agent (OPA) | M3 | downloaded binary (see [M3 README](m3-security/README.md)) → `tools/opa` |
| Ollama + `qwen2.5-coder:7b` | M4 (local LLM) | `brew install ollama` |
| Docker, k3d, kubectl, Argo CD | M6 only | `brew install k3d` |

> The `tools/` directory holds downloaded binaries (Fuseki, OPA) and is
> gitignored — fetch them once per machine using the steps in the M0 and M3
> READMEs.

### One-time setup

```bash
# from the repo root
python3 -m venv .venv

# install each module's Python deps into the shared venv
.venv/bin/pip install -r m1-ingestion/requirements.txt
.venv/bin/pip install -r m2-actions/requirements.txt
.venv/bin/pip install -r m4-ai/requirements.txt

# pull the local LLM for M4 (~4.7 GB)
ollama serve            # leave running (http://127.0.0.1:11434)
ollama pull qwen2.5-coder:7b
```

---

## Path A — local processes (M0–M5)

### Ports at a glance

| Component | Command | Port |
|-----------|---------|------|
| Fuseki (triplestore) | `./m0-ontology/serve.sh` | 3030 |
| OPA (policy decisions) | `./m3-security/run_opa.sh` | 8181 |
| Action API (M2 + M3) | `./m2-actions/run.sh` | 8000 |
| AI agent server (M4) | `cd m4-ai && ../.venv/bin/uvicorn server:app --port 8002` | 8002 |
| Web app (M5) | `./m5-app/run.sh` | 3000 |
| Ollama (host LLM) | `ollama serve` | 11434 |

### Start order

Each step says what you should see before moving on. Use a separate terminal
(or background) per long-running service.

```bash
# 1) Triplestore — leave running
./m0-ontology/serve.sh
#    -> "endpoint: http://localhost:3030/hospital"

# 2) Load the full synthetic dataset (run ONCE; supersedes M0's tiny sample)
./m1-ingestion/run.sh
#    -> "RESULT: ALL CHECKS PASSED ✅"  (10k admissions, ~64k triples)

# 3) Policy decision server — leave running
./m3-security/run_opa.sh
#    -> "Starting OPA on :8181"

# 4) Action API (admit/discharge + secure bed queries) — leave running
./m2-actions/run.sh
#    -> http://127.0.0.1:8000/docs

# 5) AI agent server — leave running (only needed for the app's "Ask" panel)
cd m4-ai && ../.venv/bin/uvicorn server:app --port 8002 ; cd ..
#    -> Uvicorn running on http://127.0.0.1:8002

# 6) Web app
./m5-app/run.sh
#    -> http://localhost:3000
```

### Use it

Open **http://localhost:3000**:

- Switch **"Acting as"** between *Carol — Bed Manager* (all wards), *Alice — Ward
  Nurse* (Ward A), and *Bob — Ward Nurse* (Ward B). The bed count and scope pill
  change with the role (M3 in action).
- **Admit** a patient to a free bed; try the **same bed twice** — the second is
  rejected with a banner, not a crash (M2 validation).
- **Discharge** to free a bed.
- Ask a natural-language question in the AI panel (M4), e.g. *"How many beds are
  free in the ICU?"* — answered from live data, scoped to your role.

Other endpoints:

- Fuseki admin UI: http://localhost:3030/
- Action API docs (Swagger): http://127.0.0.1:8000/docs

### Test everything

Run from the **repo root** unless noted. Services must be up as indicated.

```bash
# M0 — ontology loads + deliverable query (needs Fuseki)
./m0-ontology/load.sh && ./m0-ontology/query.sh
#    -> triple count, then free beds (A3, A4 on the M0 sample)

# M1 — dbt build/test + triple-count verification (needs Fuseki)
./m1-ingestion/run.sh
#    -> dbt PASS=4 / test PASS=17 ; "RESULT: ALL CHECKS PASSED ✅"

# M2 — actions + audit (needs Fuseki + Action API)
.venv/bin/python m2-actions/test_actions.py
#    -> "RESULT: 12 passed, 0 failed ✅"

# M3 — authorization (needs Fuseki + OPA + Action API)
tools/opa test m3-security/policy/ -v                 # PASS: 5/5  (no services needed)
.venv/bin/python m3-security/test_security.py         # "RESULT: 11 passed, 0 failed ✅"

# M4 — AI agent (needs Fuseki + Ollama; ~a few minutes of LLM calls)
cd m4-ai && ../.venv/bin/python test_agent.py ; cd ..
#    -> "RESULT: 10 passed, 0 failed ✅"

# M5 — app wiring (needs all backends + the app on :3000)
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3000/                       # 200
curl -s 'http://localhost:3000/api/beds?role=bed_manager'  | jq '.count, .role_scope' # 68, "ALL"
curl -s 'http://localhost:3000/api/beds?role=ward_nurse_a' | jq '.count'              # 20

# Capstone — Spark transform matches the DuckDB output (needs Docker)
./capstone/run.sh
```

### Teardown

`Ctrl-C` each long-running service. Fuseki data lives in `tools/fuseki-db/`
(gitignored, regenerable via step 2); delete that directory for a clean slate.

---

## Path B — Kubernetes via GitOps (M6)

The same five components as pods in a local **k3d** cluster, deployed and kept
in sync by **Argo CD**. The Git manifests in `m6-infra/manifests/` are the
source of truth — a commit is the deployment. Full detail in the
[M6 README](m6-infra/README.md).

```bash
# 0) prerequisite: marts built once (Path A step 2) and Ollama running on the host
# 1) cluster + Argo CD
./m6-infra/cluster-up.sh
# 2) build + import the container images (no registry)
./m6-infra/build-images.sh
# 3) point Argo CD at the manifests (public repo — no credential needed)
kubectl apply -f m6-infra/argocd/application.yaml
# 4) load synthetic data into the in-cluster Fuseki
./m6-infra/load-data.sh
# 5) open the app
kubectl -n hospital port-forward svc/app 3000:3000      # http://localhost:3000
```

**Verify the GitOps loop:**

```bash
kubectl -n hospital get pods,svc                        # all components running
kubectl -n argocd get application hospital-platform \
  -o jsonpath='{.status.sync.status} {.status.health.status}{"\n"}'   # Synced Healthy
```

Change a manifest (e.g. bump a replica count), commit, and push — Argo CD
reconciles the cluster to match Git automatically.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `Fuseki not found at …` | Download the Fuseki binary into `tools/` — see [M0 README](m0-ontology/README.md). |
| `OPA not found at …` | Download the OPA binary to `tools/opa` — see [M3 README](m3-security/README.md). |
| Action API / app returns connection errors | A dependency below it isn't up. Start order is Fuseki → OPA → Action API → agent → app. |
| M2/M3/M5 tests fail with HTTP errors | The required services aren't running (see the per-test "needs …" notes above). |
| M4 agent slow or empty answers | First run is slow while the model loads; confirm `ollama serve` is up and `qwen2.5-coder:7b` is pulled. |
| Triple counts look wrong / app shows stale data | Re-run `./m1-ingestion/run.sh` to rebuild the dataset. |
| `port already in use` | Another instance is still running on 3030 / 8000 / 8002 / 8181 / 3000 — stop it first. |
