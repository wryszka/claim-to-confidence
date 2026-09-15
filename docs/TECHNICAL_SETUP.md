# Technical setup & recovery — From Claim to Confidence

Companion to the presenter runbook (`docs/DEMO_RUN.md`). A presenter does **not** need this to
run the demo; an operator needs it to build, grant, deploy, create the Genie space, and recover.

## Target
- Workspace `fevm-lr-dev-aws-us` · profile `DEV`
- Catalog `lr_dev_aws_us_catalog` · schema `claim_to_confidence` (isolated) · evidence archive
  schema `claim_to_confidence_archive`
- Warehouse `a3b61648ea4809e3` (Serverless)
- App service principal `623c0fcf-5487-47da-a929-563f7a7b6c35`
- Model endpoint `databricks-claude-sonnet-5`
- App URL `https://claim-to-confidence-7474656169654171.aws.databricksapps.com`

## ⚠️ Current blocker (must clear first)
The Databricks profile token is invalid. Nothing below runs until you re-authenticate:
```
databricks auth login --profile DEV
```
This is an interactive browser login. All workspace-dependent acceptance rows stay `PENDING`
(see `docs/ACCEPTANCE_TESTS.md`) until this is cleared and the steps below are run live.

## Build & verify locally (no workspace)
```
python3 tools/smoke_test.py          # 43/43 oracle, to the cent
python3 tools/integration_test.py    # 31/31 control-logic checks (real server code)
```
Keep both green before deploying. `app/server/engine.py` is a copy of `tools/engine.py` —
keep them in sync (`cp tools/engine.py app/server/engine.py`).

## Deploy the scenario (idempotent reset; archives evidence first)
```
uv run --native-tls --with databricks-sdk tools/deploy_databricks.py --profile DEV
```
This archives `7_gov_audit_event`, `7_gov_run_manifest`, `6_gov_decision`, `6_gov_proposal`,
`6_gov_downstream_handoff`, `7_gov_ai_trace` into `claim_to_confidence_archive.<tbl>__<ts>`
**before** dropping, then recreates the schema and all tables (incl. the new
`0_cfg_scenario_state`, `6_gov_proposal`, `7_gov_permission_probe`, expanded `7_gov_ai_trace`,
versioned `6_gov_downstream_handoff`, and `vw_genie_position`).

## Grants (the authority model — this is the demo, get it exact)
After each deploy the schema is recreated, so re-apply. Run as the schema owner:
```sql
-- read the whole scenario
GRANT USE CATALOG ON CATALOG lr_dev_aws_us_catalog TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;
GRANT USE SCHEMA, SELECT ON SCHEMA lr_dev_aws_us_catalog.claim_to_confidence
  TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;

-- write ONLY the tables the app is allowed to mutate
GRANT MODIFY ON TABLE lr_dev_aws_us_catalog.claim_to_confidence.`7_gov_audit_event`     TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;
GRANT MODIFY ON TABLE lr_dev_aws_us_catalog.claim_to_confidence.`7_gov_ai_trace`        TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;
GRANT MODIFY ON TABLE lr_dev_aws_us_catalog.claim_to_confidence.`0_cfg_scenario_state`  TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;
GRANT MODIFY ON TABLE lr_dev_aws_us_catalog.claim_to_confidence.`6_gov_proposal`        TO `623c0fcf-5487-47da-a929-563f7a7b6c35`;
```
**Do NOT grant MODIFY on `6_gov_decision` or `7_gov_permission_probe`.** Those denials are the
authority beat: the app SP can create proposals and log traces, but Unity Catalog refuses any
approval write (Steps 8–9) and any write to the isolated permission probe (the classified
negative test). Also required:
```
databricks warehouses ... # warehouse CAN_USE for the app SP (a3b61648ea4809e3)
```
and CAN_QUERY on `databricks-claude-sonnet-5` for the app SP (for the agent screen).

To verify the invariant after granting:
```
python3 tools/preflight.py    # identity_authority note explains the invariant; run the live negative test on Screen C
```

## Deploy the app
```
# import the app dir to the workspace, then deploy from it
databricks workspace import-dir app /Workspace/Users/<you>/claim-to-confidence-app --overwrite --profile DEV
databricks apps deploy claim-to-confidence \
  --source-code-path /Workspace/Users/<you>/claim-to-confidence-app --profile DEV
```
App config is in `app/app.yaml` (env only — no secrets). Set `PRESENTER_TOKEN` to something
non-default before any shared run.

## Genie space (optional but recommended — spec §3A/§3H)
```
python3 tools/genie_space.py --print                 # inspect the definition
python3 tools/genie_space.py --create --profile DEV  # create (needs auth + CAN_MANAGE warehouse)
```
Canonical path if the CLI post rejects the payload: use the internal **genie-rooms**
GenieSpaceBuilder (see the docstring / project memory `reference_genie_space_creation.md`).
Then set `GENIE_SPACE_ID` in `app/app.yaml` and redeploy. Grant the app SP (and any presenter)
`CAN_RUN` on the space. Until then the Discover screen shows the documented setup path — not a
relabelled agent.

## The one deferred prerequisite (live reviewer approval)
Approving a **new** proposal live through the app requires a separately-authenticated reviewer
principal — a role the app SP is not. The mechanism is Databricks **Switch Roles** backed by an
**account-level group** (e.g. `c2c-chief-actuary`), which needs an **account admin** to create
(this FEVM workspace does not grant that to the operator). See `docs/SWITCH_ROLES_PLAN.md`. Once
two account groups exist, the differential grants + app OBO finish this in ~15 min. Until then
the runbook shows the **real** pre-condition enforcement + UC denial, and the seeded approved
decision (written by the reviewer role at deploy) — nothing is faked.

## Group Control Tower
`claim-to-confidence` is a node in the estate manifest (`actuarial-workbench/ESTATE_MANIFEST.yaml`)
with `/api/mcp` (`read_estimates`, `read_flagged_items`) + `vw_group_headline`/`vw_group_health`.
The hub app SP needs USE CATALOG + USE/SELECT on the schema + CAN_USE on this app.

## Recovery
- **401 / invalid token** mid-operation → re-run `databricks auth login --profile DEV`.
- **Warehouse cold** → first query wakes it (~1 min); warm before presenting.
- **App SP warehouse ACL dropped** (known estate pattern) → re-grant CAN_USE before a demo.
- **`trace NOT persisted`** on the agent screen → app SP missing MODIFY on `7_gov_ai_trace`; re-grant.
- **Gate stuck BLOCKED** → `POST /api/presenter/correct-defect?token=…` or the runbook Step 6.
- **Reset** → `POST /api/presenter/rehearsal-reset?token=…` (never drops schema/evidence).
- **Full re-verify after auth** → smoke_test · integration_test · deploy · grants · preflight ·
  runbook A–H; then update `docs/ACCEPTANCE_TESTS.md` PENDING → DEPLOYED.
