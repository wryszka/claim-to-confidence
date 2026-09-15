# Test-run handoff — From Claim to Confidence

A one-page handoff for whoever runs the end-to-end test. Full detail: `docs/DEMO_RUN.md`
(runbook) and `docs/TECHNICAL_SETUP.md` (setup/recovery).

## Entry point
- **App:** `https://claim-to-confidence-7474656169654171.aws.databricksapps.com`
- Opens on **Discover** (the business question). Sequence A–H is the left nav, top to bottom.

## Setup actions before a run
1. `databricks auth login --profile DEV` — **required now** (profile token is invalid).
2. `python3 tools/smoke_test.py` (43/43) and `python3 tools/integration_test.py` (31/31).
3. Redeploy the scenario + app and re-apply grants — see `docs/TECHNICAL_SETUP.md`
   (the schema and code changed materially; the previously-live instance is stale).
4. `python3 tools/preflight.py` → `ready=true` (Genie may be `FAIL` = optional).
5. Set a non-default `PRESENTER_TOKEN` in `app/app.yaml`; keep it to the presenter.
6. Warm the warehouse: open the app, click Discover → Decision once.

## What is proven vs pending
- **Proven locally now:** the §5 oracle (43/43) and the control logic (31/31 integration
  checks over the real server code) — gate/version, permission classification, approval
  integrity + separation of duties + staleness, reproduction from retained artifacts at
  whole-EUR precision, idempotent downstream, evidence-preserving reset, tracing-failure
  visibility, no-fabricated-APPROVED.
- **Pending live re-verification** (blocked on auth + redeploy): every workspace-dependent row
  in `docs/ACCEPTANCE_TESTS.md` is `PENDING`, not proven — including the real Unity Catalog
  approval denial, the live model/agent, tracing persistence, and the reset archive.

## Unresolved blockers
1. **Databricks auth** — profile token invalid; interactive `databricks auth login` needed
   (cannot be done unattended). Blocks all deploy / Genie / live verification.
2. **Live reviewer approval** — approving a new proposal through the app needs a separately-
   authenticated reviewer principal (account-level group via Switch Roles; needs account admin).
   The demo shows real pre-condition enforcement + UC denial + the seeded approved decision;
   the live permitted-approve path is the one deferred step. See `docs/SWITCH_ROLES_PLAN.md`.
3. **Genie space** — not yet created (`tools/genie_space.py --create` needs auth). Until then the
   Discover screen shows the documented setup path (not a relabelled agent).
4. **Validated statutory capital / IFRS 17 figure** — intentionally not asserted; downstream
   results are “awaiting recalculation”.

## Acceptance criterion
Someone who did not build this can follow `docs/DEMO_RUN.md`, demonstrate every claimed control
(gate, permission denial classified, no self-approval, stale rejected, reproduction to the euro,
idempotent downstream, evidence-preserving reset), recover from the common failures in the
runbook table, and explain why one governed workload expands into an estate.
