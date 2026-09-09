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
- `tools/engine.py` — pure Decimal calc (methods, selection, reinsurance, finance, bridge). No DB.
- `tools/world_engine.py` — deterministic scenario (seed 20260630): ledger, correction+duplicate,
  triangle, governed fixtures. Aggregates to the oracle.
- `tools/smoke_test.py` — acceptance oracle (run first, keep green).
- `tools/deploy_databricks.py` — DROP+CREATE the isolated schema, load 14 tables, write manifests.
- `app/` — FastAPI (`app.py` + `server/{config,sql,journey,engine}.py`) + `dist/index.html` SPA.
  `server/engine.py` is a copy of `tools/engine.py` (keep in sync).

## Redeploy / re-run
```bash
python3 tools/smoke_test.py                                             # prove oracle headless
uv run --native-tls --with databricks-sdk tools/deploy_databricks.py --profile DEV   # reset tables
# app: import-dir app → workspace, then: databricks apps deploy claim-to-confidence \
#   --source-code-path /Workspace/Users/<me>/claim-to-confidence-app --profile DEV
```
App SP `623c0fcf-5487-47da-a929-563f7a7b6c35` needs warehouse CAN_USE + UC USE CATALOG/SCHEMA + SELECT.

## Gotchas (fixed)
- Balancing-claim index collision undercounted case by €0.72m → distinct index (claim 41).
- Seeded draws overshot totals → scale ordinary claims to leave positive balancing headroom.
- `app.yaml` warehouse: use direct `value`, not `valueFrom: sql_warehouse`.
- Redeploy DROPS the schema (idempotent reset) — evidence-preserving reset is a follow-up.

## Deferred (next phases)
Agent + MCP surface · separately-authenticated identity enforcement · honest downstream
capital/IFRS17 numbers · Group Control Tower spine-edge integration · evidence-preserving reset.
See docs/OVERNIGHT_BUILD_LOG.md and docs/ACCEPTANCE_TESTS.md.
