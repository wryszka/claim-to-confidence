# Review report — From Claim to Confidence

> Standardized output of the 8-agent review panel (BUILD_AND_REVIEW.md §7), run fan-out (all personas in parallel) and collated here — one section per agent. Reviewed against the Bricksurance standard **v2.2**.

- **Demo:** From Claim to Confidence — `wryszka/claim-to-confidence` (live app `https://claim-to-confidence-7474656169654171.aws.databricksapps.com`)
- **Reviewed:** 2026-09-17 · live instance verified 2026-09-15 (preflight 8/8); reviewed against the deployed app + repo
- **Verdict:** **NOT YET** — one **security blocker** (SQL injection, P0) must be fixed, and several P0 *rubric-alignment* gaps are open. The demo is **substantively excellent** (financial correctness, governance, honesty, reproducibility all strong); the gaps are largely because it was built to the "refined brief," not the playbook. Fastest path to **SHIP WITH ROADMAPPED GAPS**: fix the two security items (quick), then per P0 gap either close it (DAB, house palette, DEMO_QA, `esc()`) or consciously accept-with-rationale in `DECISIONS.md` (ACORD foundation = deliberate isolated fork; managed-agent-framework, Genie-embed, `advance_period` = roadmap).
- **Scorecard (§6):** P0 ≈ **24/35** pass · P1 ≈ **16/26** pass (approximate — open items listed below).
- **Update 2026-09-17 (post-review fix):** the **security blocker is FIXED and verified live** — `proposal_id` escaped (`journey.py:75`), `esc()` hardened to all HTML-dangerous chars (`index.html`), and the presenter token now **fails closed** with no `present` default (random token in `app.yaml`). Live checks: preflight 8/8; old token refused; `' OR '1'='1` → `NO_SUCH_PROPOSAL`. The remaining NOT-YET items are **Bricksurance-standard alignment** (DAB, managed agent, Genie-embed, house palette, ACORD foundation, `DEMO_QA`, GO·DO·SAY) — **deferred: this is not a Bricksurance demo yet**, so these are logged, not required now.

**Severity:** `blocker` (a P0 fail or a deal-breaker) · `major` · `minor` · `nit`.
**Status:** `fixed` · `roadmapped` · `wontfix (reason)` · `open`.

**Panel note:** the Practitioner, Decision-maker and SA lenses each asserted an overall "SHIP / all P0 pass"; that is beyond a single lens's remit and is **not** adopted here — the collated verdict reconciles all eight. Two generous mis-reads are corrected in collation: the Decision-maker's "portable via DAB bundle" (there is **no** `databricks.yml`) and the SA's "agents managed on framework ✓ / Genie embedded ✓" (both are **gaps** per the Current-Databricks and UI/UX lenses).

---

## 1 · Practitioner (senior reserving actuary)
*Real and right in my world? Value vs. the proprietary tools I use — enrich / wrap / replace? Deal-breakers?*

| # | Finding | Severity | Answerable live? | Status |
|---|---|---|---|---|
| 1 | Reserve methods (chain-ladder, BF, 50/50 blend), the two-cutoff timing, duplicate-delivery dedup and quota-share split are all credible and correct; oracle ties to the cent. | nit | demo A–G + smoke_test | open |
| 2 | Double-count isolation is exactly how claims/finance reconcile: residual €0.2m = revised gross 41.3 − ledger 41.1; journal balanced; capital honestly "awaiting recalculation". | nit | demo B/F/G | open |
| 3 | Selection (50/50 incurred CL+BF, CDFs 1.20/1.70) is **prescribed, not shown being approved** — a real close would trace it to a governance sign-off event. Presentation gap, not an engine fault. | minor | Q&A + DECISIONS | open |
| 4 | Single accident year / single cohort / no ALR floor / no CTE / no cost-of-capital — scoped and honest, but a real book spans 10+ AYs and many LOBs. | minor | Q&A | open |
| 5 | `ledger_existing_ibnr` (€16.1m) is a point-extract as-of the valuation date — realistic for quarterly close; would drift in a daily-posting shop. Transparent assumption. | nit | world_engine.py / SPEC §5 | open |

**Deal-breakers:** none. No moment the room believes "you can't do that here" or "same as ResQ but worse" — the reserve maths, the reinsurance split, the reconciliation and the enforced approval all hold under a "show me the model/dataset/pipeline/governance" drill-down.
**Value story:** **modular** — enrich (take a ResQ reserve, add reinsurance routing + finance reconciliation + governance), wrap (governance/versioning/audit layer around the incumbent), or partial-replace (spreadsheet shops gain reproducibility + separation of duties + lineage). It won't out-sophisticate ResQ/Radar on fitted long-tail methods, and doesn't claim to.

## 2 · Decision-maker (CFO/CRO)
*Does the money and the story land? Business case, risk of inaction?*

| # | Finding | Severity | Answerable live? | Status |
|---|---|---|---|---|
| 1 | The €2m → +€2.2m gross → +€1.76m net → €0.2m residual ripple + the "already booked" banner is the risk-of-inaction beat; computed live, reproducible to the euro. | pass | demo B/H | open |
| 2 | Positioning is cooperative and honest — breadth/openness/cost, not a feature-fight; no "better-than". Matches Principle 14. | pass | all screens | open |
| 3 | The "expanding estate" (Close screen + OPERATOR_MANUAL §9) is **described, not shown** — credible for a pattern demo, but not a visual build-out. | major | Close screen text | roadmapped |
| 4 | Live second-approver deferred; capital/IFRS17 not computed; **scale not demonstrated** (41 synthetic claims); **cost/consumption not quantified**. All labelled honest roadmap. | major | Q&A / roadmap | roadmapped |

**Deal-breakers:** none found by this lens — scale, live-approver and capital are labelled roadmap, not hidden; no invented ROI/savings. A CFO would likely fund a pilot, provided the account team frames it as a pattern to fork, not a finished product.

## 3 · Databricks SA (demoability)
*Easy and reliable to demo — timings, fallbacks, reset, the yellow-button cache, live-room survival?*

| # | Finding | Severity | Answerable live? | Status |
|---|---|---|---|---|
| 1 | **No AI cache / yellow live-cached toggle** (§3.5). Agent calls run live every time — a slow model stalls the beat. | major (P1) | yes | open |
| 2 | **Not reinstallable via a DAB bundle** — no `databricks.yml`; deploy is manual `import-dir` → `apps deploy`. | blocker (P0 E) | yes | open |
| 3 | **Reset does not roll dates to today** — valuation frozen at `2026-06-30` (`world_engine.py:44`); §11 requires the as-of date to roll forward on reset. | major (P0 E) | yes | open |
| 4 | **No `STANDARDS.md` pointer** (§1) and **no `advance_period` "did it work" loop-close** (Principle 6). | major (P1) | partly | open |
| 5 | Warehouse cold-start ~1 min and model-outage both have documented fallbacks (pre-warm; honest error, financial path unaffected). Mitigated. | minor | mitigated | acceptable |

**Verdict (this lens):** survives a live room **if the runbook is followed** (warm the warehouse; know dates are fixed; know AI is live-not-cached). Preflight 8/8, hero numbers live, reset preserves evidence.

## 4 · Senior developer (correctness & robustness)
*Correct? Robust? Anything to cut? (smoke flags dead code)*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **`esc()` (`app/dist/index.html:171`) escapes only `<`** — missed `>`,`&`,`"`,`'`. The agent answer and the **adversarial claim note** flow into `.innerHTML` → XSS-adjacent. | major | **fixed** — `esc()` now escapes `& < > " '` (verified) |
| 2 | `presenter.approve` builds the `6_gov_decision` INSERT with several `prop[...]` values un-escaped (`presenter.py:170–179`) — defence-in-depth (values are DB-sourced). | minor | open |
| 3 | `journey._empirical_factor_to_ultimate` interpolates `measure` into SQL (`journey.py`) — safe today (hardcoded "PAID"/"INCURRED") but should validate in-function. | minor | open |
| 4 | `engine.py` duplicated in `tools/` and `app/server/` (kept in sync by hand) — add a `diff` pre-deploy guard to prevent drift. | minor | open |
| 5 | `sql.query_many()` swallows exceptions → `[]` (can't tell "no data" from "failed"); AI-trace errors truncated to ~200 chars. Acceptable for a demo. | nit | open |
| 6 | **Tests green:** `smoke_test.py` 43/43, `integration_test.py` 31/31. **No dead code found.** | pass | — |

## 5 · Security
*Secrets in code/history · grant scope · input escaping/binding · data egress · auth.*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **SQL injection — `journey._proposal()` (`journey.py:75`).** `proposal_id` was interpolated **unescaped** into the WHERE clause; reachable via `POST /api/presenter/approve?proposal_id=…`. `proposal_id=' OR '1'='1` bypassed the scenario filter. | **blocker (P0)** | **fixed** — `sql.esc(proposal_id)`; live `' OR '1'='1` → `NO_SUCH_PROPOSAL` |
| 2 | **Default `PRESENTER_TOKEN=present`** committed in `app.yaml`/docs/history. Combined with #1, a known token + injection was a demo-scoped hole (§6.J). | major | **fixed** — token fails closed (no default; random value in app.yaml; docs de-published); old `present` now refused live |
| 3 | Least-privilege grants (`tools/grants.py`) correct — MODIFY only on audit/ai_trace/scenario_state/proposal; the deny on decision/probe is the intended beat. | pass | — |
| 4 | Prompt-injection handled (untrusted notes labelled DATA; agent read-only + trace); no data egress; no other secrets in history. | pass | — |

**Fix before any shared/public demo:** (1) wrap `proposal_id` in `sql.esc()` at `journey.py:75`; (2) remove the hardcoded default token (empty default that must be set, or deploy-time random).

## 6 · Current-Databricks expert (up to date)
*Services/APIs current? Anything deprecated? Better primitives available?*

| # | Finding | Severity | Status | Basis |
|---|---|---|---|---|
| 1 | **Agent is a direct FMAPI call** (`agent.py` `w.serving_endpoints.query(...)`), not a managed agent. Current best is an **MLflow `ResponsesAgent`** registered as a UC model and served via the **AI Gateway** (the standard's "Agent Bricks / Mosaic AI Agent Framework" naming is older). | blocker (P0 C) | open | Databricks agents docs |
| 2 | **No DAB bundle** — deploy is manual CLI, not `bundle deploy` with minimal config (§3.5 / §6.E P0). | blocker (P0 E) | open | §3.5 |
| 3 | Genie space **created via the API** (`tools/genie_space.py` → `databricks api post /api/2.0/genie/spaces`, genie-rooms builder) — correct, avoids the SDK/raw-REST pitfall. | pass (P1) | — | §6.C |
| 4 | Hand-rolled JSON-RPC MCP endpoint (`mcp.py`) is appropriate under the "expected but evolving" forward hook. | pass (P1) | — | §3.5 |
| 5 | Model id `databricks-claude-sonnet-5` used consistently; no deprecation signals (external catalog confirmation was not available). | minor (P1) | open | — |

**Docs swept:** BUILD_AND_REVIEW §3.5/§6.C/D/E; Databricks agents (MLflow ResponsesAgent, UC AI Gateway), Genie API, serving-endpoints; the repo (agent.py, mcp.py, genie_space.py, TECHNICAL_SETUP.md) · as of 2026-09-17.

## 7 · Incumbent champion (veteran skeptic)
*Every gap / edge case / "you can't really do X" that justifies keeping the incumbent. Blunt by design.*

| # | Objection | Severity | Answered live? | Status |
|---|---|---|---|---|
| 1 | Single flat **20% quota share** — no multi-treaty, retro, layers, amendments, versioning. | major | demo only | roadmapped (Phase 1) |
| 2 | **CDFs prescribed, not fitted** — no Mack/tail curve/bootstrap CI/GLM; the "what-if" moves weights, not factors. | major | demo only | roadmapped (Phase 2) |
| 3 | **Live permitted approval deferred** — UC denial is real, the happy path is blocked (needs account admin + Switch Roles). | major | Q&A | deferred (blocker named) |
| 4 | **Capital / IFRS 17 not computed** — "awaiting recalculation". | major | demo only | roadmapped |
| 5 | **Scale unproven** — 41 synthetic claims; thousands/month, 60 cohorts, batch failure/retry not shown. | major | Q&A | roadmapped (Phase 1) |
| 6–18 | No real ledger reconciliation; defect is a UI flag not a real data break; concurrency; agent read-only (no execution tools); reproduction is retained-manifest not current-data-vs-old-code; slider is preview-only; no cross-domain integration shown; no perf/SLA. | minor–major | demo only | mostly roadmapped |

**Objections that can't be shown live → must land in `DEMO_QA.md` (which does not yet exist):** multi-treaty portfolio; fitted CDFs + CIs; why live-approval deferred; capital/IFRS17 method; scale/batch design; real reconciliation; concurrency; why agent read-only; code-change reproduction; batch failure/retry; perf/SLA; full-insurer deployment path. (The reviewer drafted straight, sourced answers for each — fold them into tab 2.)
**Bottom line (his words):** *"Honest, with a roadmap — but I'd keep ResQ for fitted methods, capital and treaty versioning and use Databricks for transparency + governance. Reconsider when Phase 1 ships multi-treaty + fitted methods."* → a **wedge-and-expand** story, not a replacement today. Not a deal-breaker, but the enrich/wrap framing must be explicit in the room.

## 8 · UI/UX expert (domain-fluent)
*Logical layout · looks good · familiar-in-seconds · anything out of place. §3 "Layout logic & UX".*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **Off the house palette** — primary accent is `--accent:#4f46e5` (indigo) everywhere, not canonical `--brand:#2563eb`; page `--bg:#f5f7fb` vs `#f1f5f9`; sidebar **256px** vs canonical **252px**. §6.F P0 "mirror, don't invent". | blocker (P0 F) | open |
| 2 | **No Learn / "how-it-works" panel and no "how does this work?" glyph** (§3 + §6.F P1) — the evidence chips show the stack, not the pedagogy. | major (P1) | open |
| 3 | **Named components not reused** — custom `.pill/.tag/.callout/.evbox/.presenter` instead of the canonical Chips/Flags/Buttons/Hero/Banner/Modal; hero + nav use custom gradients. | major (P1) | open |
| 4 | Loading `.spin` defined but not visibly triggered on async round-trips (slider recompute, Reproduce); only one responsive breakpoint (≤900), no ≤820. | minor (P2) | open |
| 5 | **Passes:** logical hierarchy (answer leads, one primary action/screen); familiar-then-better (picked up in seconds, not a clone); "What am I seeing?" on every data screen; "About this demo" disclaimer everywhere; nothing orphaned/mis-wired; clean spacing. | pass | — |

---

## Scorecard tally (§6) — open P0/P1 items

**P0 gaps (must close or consciously accept-with-rationale in DECISIONS.md):**
- **J3 Security not clean** — SQL injection + default token → **the one true blocker**.
- **E3 No DAB bundle** · **E2 reset doesn't roll dates to today** · **E1 no single Full-Build orchestrator**.
- **C6 Genie linked, not embedded** · **C8 agent not on the managed framework/AI Gateway**.
- **F1 not the house palette/components**.
- **B1 does not consume the common ACORD foundation** (isolated fork — a deliberate scope choice; accept-with-rationale or connect).
- **H1 no GO·DO·SAY run-sheet** (DEMO_RUN.md is a runbook, not the house format) · **H2 no Learn section**.
- **J2 no `DEMO_QA.md`** for the can't-show-live answers.

**P1 gaps:** no yellow live/cached toggle · Learn panel + glyph missing · no `advance_period`/reactive-loop close · no `DECISIONS.md` / data dictionary · tier not explicitly declared · reader manuals not plumbed *in-app* (they're a Google Doc + hub tile).

**Strengths (scored pass, don't lose them):** the financial spine (43/43 to the cent), real UC-enforced authority + separation of duties, reproduction to the euro from retained artifacts, honest downstream (no fabricated capital), grounded + injection-refusing agent, full audit/AI trace, three-audience docs, and a clean live preflight (8/8).

## Deal-breakers (incumbent + practitioner + decision-maker)
- **None that read as "impossible here" or "same as X but worse".** The incumbent's five HIGH items (multi-treaty, fitted CDFs, live approval, capital, scale) are **gaps to answer in Q&A + roadmap**, and land as a **wedge-and-expand** story rather than a loss — provided the enrich/wrap/replace framing is explicit and `DEMO_QA.md` exists.

## Can't-show-live list → must go to `DEMO_QA.md` (tab 2)
Multi-treaty/amendments · fitted CDFs + confidence intervals · why live-approval is deferred (Switch Roles/account group) · capital & IFRS 17 method · scale/batch design (thousands of claims, cohorts, dead-letter/retry) · real ledger reconciliation · concurrent corrections · why the agent is read-only · code-change reproduction · performance/SLA · full-insurer deployment path.

---

## Applied fixes (summary)
- **2026-09-17 — security blocker fixed + verified live** (post-review, at the user's request):
  - `journey._proposal()` — `proposal_id` now `sql.esc()`-escaped (SQL injection closed).
  - `app/dist/index.html` `esc()` — now escapes `& < > " '` (XSS-adjacent hole closed).
  - `presenter._token_ok()` — fails closed (no `present` default); `app.yaml` uses a random token; docs de-published the value.
  - Re-verified: `smoke_test` 43/43, `integration_test` 31/31, redeploy, preflight 8/8, injection → `NO_SUCH_PROPOSAL`, old token refused.
- Nothing else changed — the remaining items are the read-only review's proposals below.

## Open / roadmapped (recommended order)
1. **Security (do first, quick):** escape `proposal_id` in `journey._proposal()` (`sql.esc`); remove the hardcoded default `PRESENTER_TOKEN`; expand `esc()` in `index.html` to all HTML-dangerous chars and apply it to every `.innerHTML` API/model string. Re-run `integration_test.py`.
- 2. **Cheap rubric-alignment:** add a `databricks.yml` DAB bundle; swap the palette to `--brand #2563eb` + 252px + named components; add `STANDARDS.md`, `DEMO_QA.md` (fold in the incumbent's answers), `DECISIONS.md` (record the accept-with-rationale P0s), a data dictionary; add a GO·DO·SAY run-sheet.
- 3. **Medium:** a Learn panel + "how does this work?" glyph; the yellow live/cached AI toggle; `advance_period` reactive-loop beat; reset that rolls the as-of date to today.
- 4. **Conscious scope decisions (accept-with-rationale or roadmap):** connect to the common ACORD data foundation vs. stay an isolated fork; refactor the agent to MLflow `ResponsesAgent` on the AI Gateway; embed Genie in-app; multi-treaty + fitted CDFs + capital compute + scale (the incumbent's roadmap).
