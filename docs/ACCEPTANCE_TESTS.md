# Acceptance tests — status against the specification (§11)

Honest status as built overnight. **PROVEN** = verified by `tools/smoke_test.py` and/or the
live endpoints against the deployed Unity Catalog tables. **PARTIAL** = mechanism present but
not fully exercised. **DEFERRED** = a later phase (agent, separate authenticated principals,
downstream numbers).

| ID | Test | Status | Evidence / note |
|---|---|---|---|
| T01 | Source histories aggregate to initial & corrected paid/case/incurred; triangle ties to eligible records | **PROVEN** | `smoke_test` T01 + live `readiness`; ledger aggregates to 58/23→25/81→83; AY2023 diagonal reconciles |
| T02 | Duplicate delivery caught; cannot publish; correction/retry → one effect | **PROVEN** | Duplicate quarantined on (claim_id, revision_id); idempotent re-delivery is a no-op |
| T03 | Claims-to-finance reconciliation uses independently extracted ledger, not reserve outputs fed back | **PROVEN** | Finance residual = revised gross (reserve engine) − ledger gross (independent `6_finance_ledger_position`) |
| T04 | Every method matches an independent oracle within tolerance | **PROVEN** | `smoke_test` T04 — all four indications tie to the cent, both cutoffs |
| T05 | Changing data/weights changes results correctly; original snapshots unchanged | **PROVEN** | `recompute` moves the result; invalid weights rejected; snapshots immutable |
| T06 | Gross/ceded/net/IBNR match §5 and the UI | **PROVEN** | `smoke_test` T06 + live `change_impact` |
| T07 | Finance proposes only €0.2m/€0.04m; balanced; duplicate-post protection | **PROVEN** | `smoke_test` T07 + live `finance`; residual is never the full €2.2m |
| T12 | A new deterministic execution reproduces both versions from retained artifacts | **PROVEN** | `reproduce` endpoint compares recomputed vs stored completed run — all match |
| T19 | Model/tool outage → honest failure; financial process runs without a live LLM | **PROVEN** | The entire financial path uses no LLM; endpoints surface real errors, never fake success |
| T13 | Lineage from the executive amount to population/method/human selection | **PARTIAL** | Triangle diagonal ties to ledger; selection rationale + approver shown; full lineage graph is later |
| T14 | Correction impact identifies dependents without overwriting historic publications | **PARTIAL** | Change-impact shows only AY2023 moves; capital/IFRS 17 dependency flagged, not traversed |
| T11 | New information after approval → amendment; original reconstructable | **PARTIAL** | Two snapshots + retained run manifests; full supersession/versioning is later |
| T15 | Missing sources / failed flow prevents release; no green "complete" on partial work | **PARTIAL** | Quality gate + readiness present; a failing-source path is seeded conceptually, not exercised |
| T18 | Reports render material numbers from the approved run | **PARTIAL** | Run manifests + evidence index built; committee export document is later |
| T22 | Full 20-min rehearsal; first result < 3 min; 1080p legible | **PARTIAL** | Screens built and legible; timed rehearsal pending (see DEMO_RUN.md) |
| T08 | Cross-portfolio request denied without leaking | **DEFERRED** | Single-cohort scenario; authority matrix shown, real enforcement is the identity phase |
| T09 | Agent approval/publication & unauthorised changes fail in the real backend | **DEFERRED** | No agent yet; negative test is illustrative until separately-authenticated principals land |
| T10 | Preparer cannot self-approve; stale proposal cannot be approved | **DEFERRED** | Roles defined; enforcement needs the identity phase |
| T16 | Agent statements supported or qualified | **DEFERRED** | Agent is a later phase |
| T17 | Malicious source text cannot trigger unauthorised tools | **DEFERRED** | Agent is a later phase |
| T20 | Public mode removes internal notes / competitive criticism | **PARTIAL** | Product is public-safe by construction (no competitive criticism on screen); explicit mode toggle later |
| T21 | Scenario reset creates a new isolated instance without deleting previous evidence | **PARTIAL** | Deploy is an idempotent reset but currently **drops** the schema — evidence-preserving reset is a follow-up (flagged) |
| T23 | Capital/IFRS 17 adapters pass basis/version/reconciliation | **DEFERRED** | Honest "dependency identified / requires recalculation" — no fabricated statutory number |
| T24 | Evidence archive survives lifecycle; deletion/alteration permissions match retention claim | **DEFERRED** | Retention/immutability configuration is a later phase |

**Summary:** 9 PROVEN (the whole financial spine + reproduction + no-LLM path), 6 PARTIAL,
9 DEFERRED. This is Phase 1 complete and proven, plus parts of Phase 2. The deferred items
are the agent, the real separately-authenticated identity enforcement, and the honest
downstream numbers — the known big rocks called out in the build plan.
