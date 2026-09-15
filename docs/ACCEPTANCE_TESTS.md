# Acceptance tests — reconciled status

Each control has **one** status, an evidence reference, and an explicit distinction between
**local** verification (unit / integration, no workspace) and **deployed** verification (run
live against the isolated Unity Catalog scenario). Per the brief, workspace-dependent controls
are **not** marked proven from unit tests alone.

**Status key**
- `LOCAL ✓` — proven by `tools/smoke_test.py` (oracle) or `tools/integration_test.py` (control
  logic executed against an in-memory store using the real server code).
- `DEPLOYED …` — verification that requires the workspace.
  - `PENDING` — logic is proven locally; live verification is blocked on re-authentication
    (`databricks auth login`) + redeploy of the updated scenario/app. **Not yet re-verified live.**
  - `DEFERRED (prereq)` — needs a workspace capability we do not yet have; the exact
    prerequisite is named.

> Live verification of this build has **not** been re-run: the Databricks profile token is
> invalid (`databricks auth login` required) and the schema/app must be redeployed with the
> new tables and code. Until then every workspace-dependent row is `PENDING`, not proven.

## 1 · Financial oracle (spec §5)

| Test | Status | Evidence |
|---|---|---|
| 43 numerical checks reproduce §5 to the cent from generated inputs | **LOCAL ✓** | `tools/smoke_test.py` → 43/43 |
| Whole-EUR run results tie to the oracle (99.3 / 41.3 / 16.3 / 8.26 / 33.04; residual 0.2/0.04/0.16) | **LOCAL ✓** | `deploy_databricks.build_manifest` dry-run + `integration_test` reproduction |

## 2 · Control & integration matrix (spec §4 / §8)

| ID | Control | Local | Deployed | Evidence |
|---|---|---|---|---|
| C-GATE-1 | Failed/missing readiness controls block a new result | **LOCAL ✓** | PENDING | `integration_test` IT-GATE (defect → BLOCKED; create-proposal refused) |
| C-GATE-2 | Correcting the source releases a **new** version (old PASS doesn't carry) | **LOCAL ✓** | PENDING | IT-GATE (correct → RELEASED on new candidate version) |
| C-PERM-1 | The agent/app identity **cannot approve** | **LOCAL ✓** (models UC denial) | PENDING (real UC `PERMISSION_DENIED`) | IT-AGENT CONFIRMED_DENIAL; live = SP lacks MODIFY on `6_gov_decision` |
| C-PERM-2 | Infrastructure errors are **not** classified as permission denials | **LOCAL ✓** | PENDING | IT-AGENT INCONCLUSIVE (injected non-permission error) |
| C-PERM-3 | Unexpected write success is a **control failure**, on an isolated target | **LOCAL ✓** | PENDING | IT-AGENT CONTROL_FAILURE; write targets `7_gov_permission_probe`, never approvals |
| C-SOD-1 | Preparer cannot self-approve | **LOCAL ✓** | PENDING | IT-SOD SELF_APPROVAL |
| C-SOD-2 | An authorised reviewer can approve a current proposal | pre-conditions **LOCAL ✓** | **DEFERRED (prereq)** | IT-SOD reaches REQUIRES_REVIEWER_PRINCIPAL; the permitted write needs a separately-authenticated reviewer principal (account-level group / role-scoped login) |
| C-STALE-1 | A stale proposal cannot be approved | **LOCAL ✓** | PENDING | IT-STALE (version advanced → STALE_PROPOSAL) |
| C-APP-1 | Missing approval never displays APPROVED (no fabrication) | **LOCAL ✓** | PENDING | IT-NOAPPROVE (review NOT_APPROVED; committee unavailable; lineage “NO APPROVED DECISION”) |
| C-APP-2 | All screens/reports resolve the **same** approved artifact by explicit ids | **LOCAL ✓** | PENDING | IT-APPROVE (review/committee/lineage all = DEC-2026Q2-CM) |
| C-REPRO-1 | Historical reproduction survives changed current assumptions | **LOCAL ✓** | PENDING | IT-REPRO (reads retained manifest, not current tables) |
| C-REPRO-2 | All material outputs match at underlying (whole-EUR) precision | **LOCAL ✓** | PENDING | IT-REPRO (ultimate, gross/ceded/net, IBNR, finance residuals) |
| C-REPRO-3 | Missing artifact / unsupported calc version fails visibly | **LOCAL ✓** | PENDING | IT-REPRO (empty manifest → not reproducible; calc 9.9 → FAILED) |
| C-RPT-1 | Committee memo rendered from the approved run's retained artifacts | **LOCAL ✓** | PENDING | IT-APPROVE (committee `available` from manifest) |
| C-DOWN-1 | Downstream hand-off versioned + idempotent (no duplicate on retry) | **LOCAL ✓** | PENDING | IT-DOWNSTREAM (unique idempotency keys) |
| C-DOWN-2 | Delivery vs result state distinct; nothing fabricated / marked posted | **LOCAL ✓** | PENDING | IT-DOWNSTREAM + IT-FINANCE (GENERATED_NOT_POSTED) |
| C-TRACE-1 | AI tracing failure is surfaced, not hidden | logic **LOCAL ✓** | PENDING | `agent.ask` returns `trace.persisted`; SPA shows red badge on failure |
| C-TRACE-2 | Trace captures identity/scenario/run/response/grounding/endpoint/tool-calls/policy/correlation/timestamp | schema **LOCAL ✓** | PENDING | `7_gov_ai_trace` columns; `agent._trace` |
| C-RESET-1 | Reset preserves evidence (no schema drop, no deleted runs/audit/decision) | **LOCAL ✓** | PENDING | IT-RESET (rehearsal proposals cleared; seeded decision/manifests/audit preserved) |
| C-INJ-1 | Injection test reports response + tool activity + **caveated single-instance** outcome (no blanket “safe” badge) | logic **LOCAL ✓** | PENDING (real model) | `agent.ask` `injection_eval`; SPA shows instance outcome + caveat |
| C-GENIE-1 | Genie distinguishes proposed / approved / outstanding | view logic **LOCAL ✓** | **DEFERRED (prereq)** | `vw_genie_position.position_status`; needs the Genie space (`tools/genie_space.py`) |
| C-AUTH-1 | Presenter mutations are POST + token-gated (off the audience path) | **LOCAL ✓** | PENDING | IT-AUTH (refused without token); endpoints are POST-only |

## 3 · Original spec acceptance tests (T01–T24) — mapping

| ID | Test | Status | Note |
|---|---|---|---|
| T01–T07 | Financial spine (aggregation, dedup, reconciliation, methods, weights, reinsurance, residual) | **LOCAL ✓** | smoke_test; DEPLOYED PENDING |
| T08 | Cross-portfolio request denied without leaking | **LOCAL ✓** (policy) / DEPLOYED PENDING | agent forbidden-action denial; multi-portfolio leak testing out of scope |
| T09 | Agent approval fails in the real backend | **LOCAL ✓** (modelled) / DEPLOYED PENDING | C-PERM-1; live = UC denial after redeploy |
| T10 | Preparer cannot self-approve; stale cannot be approved | **LOCAL ✓** | C-SOD-1 + C-STALE-1; the *permitted* human path = C-SOD-2 DEFERRED |
| T11 | New info after approval → amendment; original reconstructable | **LOCAL ✓** (versions + retained manifests) / DEPLOYED PENDING | next-version + reproduce previous |
| T12 | Deterministic reproduction of both versions | **LOCAL ✓** | C-REPRO-1/2 |
| T13 | Lineage executive amount → population/method/human | **LOCAL ✓** / DEPLOYED PENDING | `journey.lineage` |
| T14 | Correction identifies dependents without overwriting history | **LOCAL ✓** / DEPLOYED PENDING | downstream hand-off + evidence archive |
| T15 | Missing sources / failed flow prevents release | **LOCAL ✓** | C-GATE-1/2 |
| T16 | Agent statements supported or qualified | DEPLOYED PENDING | real model; grounded prompt + FACT/HYPOTHESIS contract |
| T17 | Malicious source text cannot trigger unauthorised tools | DEPLOYED PENDING | C-INJ-1; single-instance, caveated |
| T18 | Reports render material numbers from the approved run | **LOCAL ✓** | C-RPT-1 |
| T19 | Model/tool outage → honest failure; financial path runs without a live LLM | **LOCAL ✓** | financial path uses no LLM; `_safe` surfaces real errors |
| T20 | Public mode removes internal notes / competitive criticism | **LOCAL ✓** (by construction) | no competitive criticism on any screen |
| T21 | Scenario reset creates a new instance without deleting evidence | **LOCAL ✓** (rehearsal reset) / DEPLOYED PENDING (archive-before-drop) | C-RESET-1; deploy archives to `claim_to_confidence_archive` |
| T22 | Full rehearsal; first result early; 1080p legible | DEPLOYED PENDING | runbook ready; timed rehearsal needs a live presenter |
| T23 | Capital/IFRS17 adapters pass basis/population/version | **LOCAL ✓** (honest hand-off) | no fabricated statutory number; validated figure DEFERRED |
| T24 | Evidence archive survives lifecycle; delete/alter perms match retention | **LOCAL ✓** (archive) / DEPLOYED PENDING | immutable-retention config is a later phase |

## What must be re-verified live (once `databricks auth login` + redeploy)
Run, in order: `python3 tools/smoke_test.py` · `python3 tools/integration_test.py` ·
redeploy (`docs/TECHNICAL_SETUP.md`) · `python3 tools/preflight.py` · then the full runbook
sequence A–H, recording the app revision, warehouse, results and any remaining limitation here.
Only after that may the `PENDING` rows become `DEPLOYED ✓`.
