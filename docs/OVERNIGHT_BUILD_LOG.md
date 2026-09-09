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

## Watch-outs for the next session

- The app SP's warehouse ACL is known to get dropped across the estate periodically
  (documented pattern) — re-check `CAN_USE` before a demo.
- Redeploying the scenario **drops and recreates** the schema (idempotent reset) — fine for a
  demo instance, but do not point anything precious at it.
- The favicon 404 in the console is harmless (no favicon shipped).
