# M5 — Application Layer

The operational interface end-users touch: live ward occupancy, guarded
Admit/Discharge controls, a role-scoped view, and an embedded AI query box. It
ties every prior module together into one app.

**Next.js (App Router) + TypeScript.** Synthetic data only — never real PHI.

## Architecture

The browser only ever talks to this app. Next.js **route handlers** (server-side)
proxy to the backend services, so there is no CORS and backend URLs stay server-side:

```
 Browser ──▶ Next.js route handlers ──▶ M2 action API (:8000) ──▶ Fuseki / OPA
 (page.tsx)   app/api/{beds,admit,        /secure/beds, /admit, /discharge
              discharge,ask}/route.ts ──▶ M4 agent service (:8002) ──▶ Ollama
```

| Piece | Role |
|-------|------|
| `app/page.tsx` | Dashboard (client): summary cards, bed grid, actions, agent box. |
| `app/api/beds/route.ts` | Role-scoped occupancy ← `M2 /secure/beds` (M3 policy). |
| `app/api/admit/route.ts` · `discharge/route.ts` | Guarded actions ← `M2 /admit` `/discharge`. |
| `app/api/ask/route.ts` | NL question ← `M4 agent service` (optional). |
| `lib/api.ts` | Backend URLs + role→identity map (`bed_manager`→`manager_carol`, …). |

### Role scoping (M3, visible in the UI)

The "Acting as" selector chooses an identity. Every bed query carries it as
`X-User`, so the M3 OPA policy scopes the result: **Bed Manager sees all 4 wards
(68 beds); a Ward Nurse sees only their ward (20).** The visible-scope pill and
the bed grid both reflect it.

### Guarded actions (M2)

Free beds show an *Admit* control (enter a patient id); occupied beds show
*Discharge*. Both call the validated M2 API. A rejected admit (occupied bed) comes
back as a 409 and is shown in a red banner with the rule message — the app
**degrades gracefully**, it doesn't crash or write.

### AI box (M4, optional)

"Ask the data" sends a natural-language question to the M4 agent, scoped to the
current role. Requires the agent service (`m4-ai/server.py`); if it's not
running, the box shows a friendly message and the rest of the app works.

## Prerequisites

- Node.js 18.18+ (tested on Node 24). `npm install` in this folder.
- Running backends: **Fuseki** (`m0-ontology/serve.sh`), **OPA**
  (`m3-security/run_opa.sh`), **action API** (`m2-actions/run.sh`).
- Optional for the AI box: `cd m4-ai && ../.venv/bin/uvicorn server:app --port 8002`.

Backend URLs are overridable via `ACTION_API` / `AGENT_API` env vars.

## How to run

```bash
./m5-app/run.sh            # installs deps if needed, starts dev server on :3000
# or:  cd m5-app && npm install && npm run dev
```

Open http://localhost:3000, switch the "Acting as" role, and admit/discharge.

## How to verify

With the backends up and the app running:

```bash
# 1. page renders
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3000/         # 200

# 2. role scoping (M3) through the app
curl -s 'http://localhost:3000/api/beds?role=bed_manager'  | jq '.count, .role_scope'   # 68, "ALL"
curl -s 'http://localhost:3000/api/beds?role=ward_nurse_a' | jq '.count'                # 20 (Ward A)

# 3. guarded action + graceful rejection (M2)
curl -s -X POST http://localhost:3000/api/admit -H 'Content-Type: application/json' \
  -d '{"patient_id":"SYN-PWEB1","bed_code":"A11","role":"ward_nurse_a"}' | jq '.result'  # "admitted"
curl -s -X POST http://localhost:3000/api/admit -H 'Content-Type: application/json' \
  -d '{"patient_id":"SYN-PWEB2","bed_code":"A11","role":"ward_nurse_a"}' | jq '.detail.reasons'  # rejected
curl -s -X POST http://localhost:3000/api/discharge -H 'Content-Type: application/json' \
  -d '{"bed_code":"A11","role":"ward_nurse_a"}' | jq '.result'           # "discharged"
```

### Assessment criteria → evidence

- [x] **Dashboard reflects current triplestore state** — `/api/beds` reads live from
  Fuseki on every load/refresh and after each action.
- [x] **Admit/Discharge invoke the validated action API** — via `/api/admit` `/api/discharge` → M2.
- [x] **Role scoping is visible** — role selector + scope pill; manager=68 vs nurse=20.
- [x] **Degrades gracefully on rejection** — 409 shown as a banner; no crash, no write.

> This is a single-user demo UI: no auth/session (the role selector is a stand-in
> for real authentication), no optimistic concurrency. See the capstone
> "what this is NOT".
