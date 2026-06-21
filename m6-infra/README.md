# M6 — Infrastructure & Delivery

Containerise the platform, run it on **Kubernetes (k3d)**, and deliver it with
**GitOps (Argo CD)**: the cluster reconciles itself to match manifests in Git.
A commit is the deployment.

**Synthetic data only — never real PHI. Local cluster only.**

## What runs where

```
            ┌─────────────────────── k3d cluster ───────────────────────┐
 git push ─▶│  Argo CD  ──watches Git──▶  namespace: hospital            │
 (manifests)│                              fuseki · opa · action-api      │
            │                              agent · app                    │
            └───────────────────────────────────────────────────────────┘
                                              │ agent → host.k3d.internal
                                              ▼
                                     Ollama on the host (M4 model)
```

| Component | Image | Notes |
|-----------|-------|-------|
| `fuseki` | `hospital/fuseki:local` | Self-contained Jena Fuseki 6.1.0 (in-memory `/hospital`). |
| `opa` | `openpolicyagent/opa` | Policy from a ConfigMap (the M3 Rego + user data). |
| `action-api` | `hospital/action-api:local` | M2 FastAPI. |
| `agent` | `hospital/agent:local` | M4 agent; reaches the **host** Ollama via `host.k3d.internal`. |
| `app` | `hospital/app:local` | M5 Next.js dashboard. |

Images are built locally and `k3d image import`-ed (no registry). Ollama stays on
the host — putting a 4.7GB model in-cluster isn't worth it on a laptop.

## Files

| Path | What it is |
|------|------------|
| `images/fuseki/Dockerfile` | Builds the Fuseki image. |
| `../m2-actions/Dockerfile` · `../m4-ai/Dockerfile` · `../m5-app/Dockerfile` | The three app images. |
| `manifests/` | Deployments + Services (+ OPA ConfigMap) — **the GitOps source of truth**. |
| `argocd/application.yaml` | The Argo CD `Application` pointing at `manifests/` in this repo. |
| `cluster-up.sh` · `build-images.sh` · `load-data.sh` | Setup helpers. |

## Prerequisites

- Docker running; **k3d** + **kubectl** installed (`brew install k3d`).
- The local images' source builds (M2/M4/M5) and the M1 DuckDB marts present
  (run `m1-ingestion/run.sh` once) for data loading.
- Ollama running on the host (M4).
- This repo pushed to the Git URL in `argocd/application.yaml` (Argo pulls from there).

## How to run

```bash
# 1. cluster + Argo CD
./m6-infra/cluster-up.sh

# 2. build + import the images
./m6-infra/build-images.sh

# 3. tell Argo CD to deploy from Git (private repo needs a repo credential)
kubectl apply -f m6-infra/argocd/application.yaml

# 4. load synthetic data into the in-cluster Fuseki
./m6-infra/load-data.sh

# 5. open the app
kubectl -n hospital port-forward svc/app 3000:3000   # http://localhost:3000
```

For a **private** repo, create the Argo CD repo credential first:

```bash
kubectl -n argocd create secret generic repo-hospital \
  --from-literal=type=git \
  --from-literal=url=https://github.com/<you>/reference-ontology-platform.git \
  --from-literal=username=<you> \
  --from-literal=password=$(gh auth token)
kubectl -n argocd label secret repo-hospital argocd.argoproj.io/secret-type=repository
```

## How to verify

```bash
# all components are pods, reachable via services
kubectl -n hospital get pods,svc

# Argo CD reports the app Synced + Healthy
kubectl -n argocd get application hospital-platform \
  -o jsonpath='{.status.sync.status} {.status.health.status}{"\n"}'   # Synced Healthy
```

### GitOps reconcile demo

Change `manifests/30-action-api.yaml` `replicas: 1 → 2`, commit, push. Argo CD
detects the change and scales the Deployment with no `kubectl apply`:

```bash
kubectl -n hospital get deploy action-api -w   # watch it go 1 → 2
```

### Assessment criteria → evidence

- [x] **All components run as pods, reachable via services** — `kubectl get pods,svc`.
- [x] **Argo CD shows Synced/Healthy** — the status command above.
- [x] **A Git commit triggers an automatic cluster change** — the replica-bump demo.
- [x] **GitOps vs manual `kubectl apply`** — see below.

### GitOps reconciliation vs `kubectl apply`

With `kubectl apply` you *push* changes imperatively and nothing stops the live
state from drifting. With GitOps, Git is the single source of truth and Argo CD
*pulls* — continuously reconciling the cluster to match the repo (and, with
`selfHeal`, reverting manual drift). The deploy is a reviewed, audited commit, and
the cluster's real state is always the declared state.

> Not production: single-node, in-memory Fuseki, locally-imported images (no
> registry/signing), illustrative Argo config. See the capstone "what this is NOT".
