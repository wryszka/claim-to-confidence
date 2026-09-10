# Overnight build log — From Claim to Confidence

Built autonomously overnight on 9–10 September 2026 from the "From Claim to Confidence"
specification and the reviewed build plan, while the user slept. This is the honest record
of what was decided, built, proven and left open.

## Decisions taken (the four open questions in the build plan)

These were answered with reversible defaults because the user was asleep; all are cheap to change.

1. **Timeline** — target 30 September; prioritised a *proven, real* Phase 1 + a *wow* visible
   journey over breadth.
2. **Downstream (capital / IFRS 17)** — stayed honest: the journey shows "dependency
   identified", never a fabricated statutory number.
3. **Identity** — real backend authority is described and the negative test is shown, but
   separately-authenticated principals are deferred (documented); first cut uses a labelled
   role harness.
4. **Currency** — committed to EUR per the specification.
5. **Vehicle** — built an **isolated scenario instance** (`claim-to-confidence`, own schema)
   forked from the proven Reserving Workbench engine, so the live Hiscox demo is untouched.
   The executive screens are built to port into the Group Control Tower (the agreed production
   home); the standalone app is the reliable path to a wow Phase-1 demo.

## What was built

- **Pure calculation engine** (`tools/engine.py`) — methods, selection, reinsurance, finance
  residual, movement bridge. Decimal, exact to the cent. No database dependency.
- **Deterministic scenario generator** (`tools/world_engine.py`) — a real AY2023 claim ledger
  that aggregates to the oracle, the €2m correction with two clocks, the duplicate delivery
  defect, a derived triangle, and all governed fixtures.
- **Acceptance oracle** (`tools/smoke_test.py`) — **43/43 checks green, to the cent.**
- **Databricks deploy** (`tools/deploy_databricks.py`) — 14 Unity Catalog tables in the
  isolated schema `lr_dev_aws_us_catalog.claim_to_confidence`, plus retained run manifests
  and a persisted completed run.
- **FastAPI backend** (`app/`) — reads the real tables and computes every screen live through
  the same proven engine. Verified live: hero 2.0/2.2/1.76, residual 0.2, reproduce matches.
- **Single-page app** (`app/dist/index.html`) — six screens (A–F), punchy executive hero, the
  claim→reserve→reinsurance→finance→capital ripple, the double-count reveal, the what-if
  slider, the revision bridge, the four-numbers card, the authority matrix + negative test,
  and deterministic reproduction.
- **Deployed and running** at `https://claim-to-confidence-7474656169654171.aws.databricksapps.com`
  (app service principal granted warehouse CAN_USE + Unity Catalog USE/SELECT).
- Screenshots in `docs/` (Screen A, Screen D). Full docs: README, ORACLE, ACCEPTANCE_TESTS,
  DEMO_RUN, this log.

## What is proven (see ACCEPTANCE_TESTS.md)

9 acceptance tests fully proven — the entire financial spine (T01–T07), deterministic
reproduction (T12), and the no-LLM honest-failure path (T19) — verified both headless and live
against the deployed tables. 6 partial, 9 deferred.

## What is deferred (the known big rocks)

- **The Senior Reserving Actuary agent** and its MCP tool surface (extend the existing one).
- **Separately-authenticated identity enforcement** (the real negative test, T08–T10). The
  Group Control Tower's named-principal mechanism is the foundation.
- **Honest downstream numbers** — capital / IFRS 17 stay "dependency identified" until a
  supported, independently-validated number is available.
- **Group Control Tower integration** — turning the estate-manifest spine edges live
  (claims→reserving→reinsurance→finance). The screens are built to port.
- **Evidence-preserving reset** — the deploy currently *drops* the schema on redeploy; a reset
  that archives prior evidence (T21) is a follow-up.

## Gotchas hit and fixed

- **Claim-ID collision** — the balancing claim reused the last generated claim's index, so its
  case estimate overwrote in per-claim aggregation and the case total came out €0.72m short.
  Fixed by giving the balancing claim a distinct index (claim 41).
- **Seeded draws overshot** the cohort totals → negative balancing claim. Fixed by scaling the
  39 ordinary claims to leave positive headroom for an exact balancing claim.
- **Warehouse binding** — switched `WAREHOUSE_ID` from `valueFrom: sql_warehouse` to a direct
  value in `app.yaml` to avoid a resource-binding failure mode.
- Warehouse was STOPPED at deploy time; it wakes on first query (cold-start ~1 min).

## 2026-09-10 — Group Control Tower integration

Wired `claim-to-confidence` into the estate's Group Control Tower (in the `actuarial-workbench`
repo) as a **live node**, per the tower's manifest-driven contract:
- Added an `/api/mcp` JSON-RPC endpoint (`app/server/mcp.py`) with `read_estimates` (headline
  KPIs) and `read_flagged_items` (attention queue). Verified live: `tools/list` + `tools/call`
  return the correct figures (gross 41.3 / net 33.04 / +2.2 / +1.76 / residual 0.2; 4 attention items).
- Published two views the tower reads directly: `vw_group_headline` (journey KPIs) and
  `vw_group_health` (control status) — folded into `deploy_databricks.py` for reproducibility.
- Added the node + adapter + two planned spine edges (claims→c2c→reinsurance) to
  `actuarial-workbench/ESTATE_MANIFEST.yaml`; the tower is 100% manifest-driven, no code edits.
- Granted the **hub's** app service principal (`7d88f801-…`) USE CATALOG + USE/SELECT on the
  `claim_to_confidence` schema, and CAN_USE on the c2c app (for the MCP calls + audit union).
- Deployed the hub. **Verified:** the served `/api/group/manifest` now lists 9 nodes incl.
  `claim-to-confidence`.

**Gotcha:** `make deploy-dev` runs `cp ESTATE_MANIFEST.yaml src/app/` in `build`, but the first
`databricks bundle deploy` did **not** sync the updated manifest into the deployed bundle path.
Fix: `databricks workspace import` the manifest straight to the app's `source_code_path` and
`databricks apps deploy` from there. (Re-check this on the next hub deploy.)

**Caveat:** the tower's `/api/group/warmup` (which reads every node's views + calls each MCP)
**504s** when many nodes are cold — an estate-wide cold-warm characteristic, not a c2c defect.
The board caches the last successful warm (`gct_cache_snapshot`); c2c's headline appears once a
warm completes. `/api/group/state` and `/api/group/board` are SPA routes, not JSON APIs — the
board data is the warmed snapshot.

## 2026-09-10 — the rest: downstream, lineage, gate, reset, committee memo

Delivered the remaining self-contained items (Option B / Switch Roles skipped per decision):
- **Honest downstream hand-off (T23)** — `6_gov_downstream_handoff` passes the affected inputs
  (net/gross/ceded movement, currency, valuation, cohort map, source decision id) to capital
  (Solvency II SCR) and IFRS 17 (LIC + reinsurance-held), each marked `REQUIRES_RECALCULATION`
  / `MAPPING_UNRESOLVED`. **No fabricated statutory number.** Shown in Change impact.
- **Lineage (T13)** — `/api/lineage` renders the 7-level chain executive amount → human decision
  → selection → method indications → triangle diagonal (ties to ledger to the penny) →
  population (payments) → source deliveries. Shown in Decision & evidence.
- **Readiness gate + DQ controls (T15)** — `1_raw_dq_check` + a gate that computes RELEASED/BLOCKED
  (a critical FAIL blocks release). Shown in Data readiness with per-check status.
- **Evidence-preserving reset (T21)** — the deploy now archives audit / run manifests / decision /
  AI trace into a timestamped `claim_to_confidence_archive` schema **before** dropping. Verified:
  4 tables archived on the reset (suffix `__20260910_095536`).
- **Committee memo (T18)** — `/api/committee-report` renders the memo from the approved
  `6_gov_decision` — the figures are the booked selection, not free text.
- All redeployed and verified live; acceptance now **17 proven** (see ACCEPTANCE_TESTS.md).
  Screenshot: `docs/screen_F_evidence.png`.

## Watch-outs for the next session

- The app SP's warehouse ACL is known to get dropped across the estate periodically
  (documented pattern) — re-check `CAN_USE` before a demo.
- Redeploying the scenario **drops and recreates** the schema (idempotent reset) — fine for a
  demo instance, but do not point anything precious at it.
- The favicon 404 in the console is harmless (no favicon shipped).
