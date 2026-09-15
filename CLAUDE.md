# claim-to-confidence — build notes

## What this is
Isolated scenario instance implementing the "From Claim to Confidence" spec: one €2m claim
correction traced through reserve → reinsurance → finance → capital for Bricksurance SE
(fictional, synthetic). Forked from the Reserving Workbench engine so it never touches the
live Hiscox demo. Executive screens built to port into the Group Control Tower.

## Non-negotiables (user instructions)
- **Runs for real on Databricks** — real Unity Catalog tables + app SP; never fake. No
  browser-side reserve maths, no fabricated results, no fake jobs.
- The engine **derives answers from inputs**; `tools/smoke_test.py` holds the independent
  §5 oracle and must stay green (43/43, to the cent) before anything is built on top.
- Every screen: "what am I seeing" explainer + a persistent demo disclaimer. Cooperative
  positioning only on any public/product surface — competitive framing lives in presenter notes.
- uv `--native-tls`, not pip/npm. Claude via FMAPI (`databricks-claude-sonnet-5`) when the
  agent is added (deferred).

## Target
DEV `fevm-lr-dev-aws-us` (profile DEV) · catalog `lr_dev_aws_us_catalog` · schema
`claim_to_confidence` · warehouse `a3b61648ea4809e3` (Serverless). Public repo
`wryszka/claim-to-confidence` (gh: `auth switch -u wryszka` first).

## Architecture
- `tools/engine.py` — pure Decimal calc (methods, selection, reinsurance, finance, bridge) +
  `assumption_fingerprint` + `CALC_VERSION`. No DB.
- `tools/world_engine.py` — deterministic scenario (seed 20260630): ledger, correction+duplicate,
  triangle, governed fixtures. Aggregates to the oracle.
- `tools/smoke_test.py` — §5 oracle (run first, keep green; 43/43).
- `tools/integration_test.py` — §8 control-logic checks over the REAL server code via an
  in-memory table store (31/31; stale/self-approval/gate/reproduction/idempotency/reset/etc.).
- `tools/deploy_databricks.py` — archive evidence → DROP+CREATE the isolated schema → load tables
  + `0_cfg_scenario_state`, `6_gov_proposal`, `6_gov_decision`, `6_gov_downstream_handoff`
  (versioned), `7_gov_permission_probe` (isolated), expanded `7_gov_ai_trace`, `vw_genie_position`;
  write retained manifests (whole-EUR results + calc/input version + retention).
- `tools/genie_space.py` — build/create the Genie space (§3A/§3H).
- `tools/preflight.py` — CLI that calls the app's `/api/preflight` (runs as the app SP).
- `app/` — FastAPI (`app.py` + `server/{config,sql,journey,agent,mcp,presenter,engine}.py`) +
  `dist/index.html` SPA (9 screens A–I: Discover(Genie)→Decision→Investigate→Data quality→
  Judgement→Approval→Downstream→Prove it→Close, each with a §5 "view evidence" chip + a collapsed
  presenter panel). `server/engine.py` is a copy of `tools/engine.py` (keep in sync).
- `server/presenter.py` — authenticated (PRESENTER_TOKEN) POST mutations, scoped by scenario id:
  introduce/correct defect, create proposal, approve (real UC denial), next-version, rehearsal-reset.

## Redeploy / re-run
```bash
python3 tools/smoke_test.py            # oracle 43/43
python3 tools/integration_test.py      # control logic 31/31
cp tools/engine.py app/server/engine.py                                 # keep engine in sync
uv run --native-tls --with databricks-sdk tools/deploy_databricks.py --profile DEV
# grants (see docs/TECHNICAL_SETUP.md) — MODIFY on audit/ai_trace/scenario_state/proposal ONLY;
#   NOT on 6_gov_decision or 7_gov_permission_probe (those denials are the authority beat)
# app: import-dir app → workspace, then databricks apps deploy claim-to-confidence …
python3 tools/preflight.py             # ready=true
```
App SP `623c0fcf-5487-47da-a929-563f7a7b6c35`: warehouse CAN_USE + UC USE CATALOG/SCHEMA/SELECT +
MODIFY on the four writable tables + CAN_QUERY on databricks-claude-sonnet-5.

## Gotchas (fixed)
- Balancing-claim index collision undercounted case by €0.72m → distinct index (claim 41).
- Seeded draws overshot totals → scale ordinary claims to leave positive balancing headroom.
- `app.yaml` warehouse: use direct `value`, not `valueFrom: sql_warehouse`.
- Redeploy archives evidence to `claim_to_confidence_archive` BEFORE dropping (reset ≠ delete).
- Reproduction reads the RETAINED manifest inputs, never the current tables (whole-EUR compare).

## Deferred (exact prerequisites)
- **Live reviewer approval** — needs an account-level group (Switch Roles); needs account admin.
  Pre-conditions + UC denial are real; the permitted-approve path is the only faked-free gap.
- **Genie space creation** — needs auth + CAN_MANAGE warehouse (`tools/genie_space.py --create`).
- **Validated statutory capital/IFRS17 figure** — intentionally honest-only ("awaiting recalculation").
- **Live re-verification** — blocked on `databricks auth login`; all workspace rows in
  docs/ACCEPTANCE_TESTS.md are PENDING until redeploy + the runbook is run live.
See docs/DEMO_RUN.md (runbook), docs/TECHNICAL_SETUP.md, docs/ACCEPTANCE_TESTS.md, docs/TEST_RUN_HANDOFF.md.
