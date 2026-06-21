# M3 — Dynamic Security

Role- and attribute-based access enforced **at request time**, so the *same*
query returns *different* results per user. Permissions are not baked into the
data — they are a policy decision, made by **Open Policy Agent (OPA)** from a
Rego policy that lives entirely outside the application code.

**Synthetic data only — never real PHI.**

## Concept

A `ward_nurse` should see only their own ward; a `bed_manager` sees everything.
Before answering a bed query, the API asks OPA *"can this user view beds, and
scoped to which ward?"*. OPA returns `{allow, ward_filter}`; the API enforces it
by injecting the ward filter into the SPARQL. Change the policy or the user→ward
data and behaviour changes with **no app redeploy**.

## What this module contains

| Path | What it is |
|------|------------|
| `policy/authz.rego` | The Rego policy: roles → allow/deny + ward filter. |
| `policy/data.json` | User → role/ward assignments (data, not code). |
| `policy/authz_test.rego` | Rego unit tests for the policy. |
| `run_opa.sh` | Run OPA as a decision server on `:8181`. |
| `test_security.py` | End-to-end verification against the live API. |

The integration into the API is two small pieces in the M2 app:
`m2-actions/app/authz.py` (the OPA client) and the `GET /secure/beds` endpoint
in `app/main.py`. **The app contains no access rules** — it only calls OPA and
injects the returned filter.

### The policy

```
bed_manager  -> { allow: true,  ward_filter: "" }        # all wards
ward_nurse   -> { allow: true,  ward_filter: <own ward> } # scoped
ward_nurse asking for another ward -> { allow: false }    # denied
unknown user -> { allow: false }                          # deny by default
```

Roles and ward assignments come from `data.json`
(e.g. `nurse_alice → Ward A`, `manager_carol → bed_manager`).

## Prerequisites

- **OPA 1.x** at `../tools/opa` (downloaded binary, gitignored). To install:
  ```bash
  curl -sSL -o tools/opa https://openpolicyagent.org/downloads/latest/opa_darwin_amd64
  chmod +x tools/opa
  ```
- Fuseki (`m0-ontology/serve.sh`) with M1 data, and the M2 API (`m2-actions/run.sh`).

## How to run

```bash
# terminal 1: Fuseki      ./m0-ontology/serve.sh
# terminal 2: OPA         ./m3-security/run_opa.sh
# terminal 3: action API  ./m2-actions/run.sh
```

Same request, two identities, two different result sets:

```bash
curl -s localhost:8000/secure/beds -H 'X-User: manager_carol' | jq '.role_scope, .count'
# "ALL", 68

curl -s localhost:8000/secure/beds -H 'X-User: nurse_alice'   | jq '.role_scope, .count'
# "Ward A", 20
```

## How to verify

```bash
# policy unit tests (no services needed)
tools/opa test m3-security/policy/ -v        # PASS: 5/5

# end-to-end against the running API + OPA
.venv/bin/python m3-security/test_security.py
```

Expected (11 checks, all pass):

```
manager_carol  -> 68 beds across [ICU, Ward A, Ward B, Ward C]
nurse_alice    -> 20 beds, scope=Ward A
nurse_bob      -> 20 beds, scope=Ward B
one request, different roles -> DIFFERENT result sets
nurse_alice asking for ICU   -> 403 denied
unknown user                 -> 403 denied
RESULT: 11 passed, 0 failed ✅
```

### Assessment criteria → evidence

- [x] **Ward nurse sees only their ward's beds** — `nurse_alice` → Ward A (20).
- [x] **Bed manager sees all beds** — `manager_carol` → all 68 / 4 wards.
- [x] **Policy is external to application code** — rules are in `policy/authz.rego`
  + `data.json`, evaluated by OPA; the app only calls `decide()` and injects the
  filter.
- [x] **Contrast with static table-level permissions** — see below.

### Dynamic vs static permissions

Static, table-level grants (e.g. SQL `GRANT SELECT ON beds`) are coarse: a user
either sees the whole table or none of it, and changing the rule means a schema
migration. Here the decision is made **per request, per object dimension** (ward)
by a policy that is versioned, unit-tested, and hot-swappable independently of
the app and the data — the same `/secure/beds` call yields a different, correctly
scoped result for each caller.

> The injected ward filter is still escaped as a SPARQL literal (`_q`) before it
> reaches the query, so a policy/data value can't become an injection vector.
> This is an *illustrative* access model, not production authn/secrets/network
> hardening — see the capstone "what this is NOT".
