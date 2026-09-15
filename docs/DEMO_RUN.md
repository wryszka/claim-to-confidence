# Internal presenter runbook — From Claim to Confidence

**Audience:** senior commercial leadership (limited insurance knowledge).
**What it shows:** one €2m claim correction, traced as a governed decision across reserve →
reinsurance → finance → downstream, with enforced authority and reproducible evidence.
**App:** `https://claim-to-confidence-7474656169654171.aws.databricksapps.com`
**Companion:** technical setup, grants, recovery and the pending prerequisite are in
`docs/TECHNICAL_SETUP.md`. You do **not** need the build log to run this.

Cooperative framing throughout: *AI makes the individual task easier; this journey shows what
it takes to operate the resulting decision across the business.* Never disparage spreadsheets
or claim a platform "guarantees compliance" — the point is connected, governed, reproducible.

Define **reserve** once, then never again: *an insurer's estimate of money it still expects to
pay for claims that have already happened.*

The steps are numbered, not timed. Aim to reach a business result (Step 6) early. Each step
lists: starting state · action · prompt · expected result · talk track · why it matters ·
Databricks service · pass/fail · recovery · scope limits.

---

## Step 0 — Preflight (before the audience is in the room)

1. **Starting state:** nothing open.
2. **Action:** run `python3 tools/preflight.py` (or open `/api/preflight` in an authenticated
   tab). Then open the app and click through Discover → Decision once to warm the warehouse.
3. **Prompt:** none.
4. **Expected result:** every required check `PASS` and `ready=true`. Genie may show `FAIL`
   (optional) if the space is not yet created — that is acceptable (native-link fallback).
5. **Talk track:** none (setup).
6. **Why it matters:** a healthy web page is not a healthy demo — the preflight checks the
   warehouse, tables, approved decision, reproduction, model endpoint, tracing and identity.
7. **Databricks service:** Databricks Apps, SQL warehouse, Unity Catalog, Model Serving.
8. **Pass/fail:** `ready=true` (Genie excluded). If not, read the failing item's message.
9. **Recovery:** warehouse asleep → the first query wakes it (~1 min); re-run. Table missing →
   redeploy (`docs/TECHNICAL_SETUP.md`). Model endpoint down → the agent step shows an honest
   outage; the financial path is unaffected — skip Step 5's live call or use the trace history.
10. **Scope limits:** preflight runs as the app service principal — it reflects what the demo
    identity can do, not your personal access.

## Step 1 — Identities & access (know before you present)

- The app runs as **one service principal** with SELECT on the scenario schema and MODIFY only
  on the audit / AI-trace / scenario-state / proposal tables — **not** on the approvals table.
  That single fact is the authority beat (Steps 8–9): the app literally cannot approve.
- The **presenter utility** (Step 7's defect flow, Step 9's approval attempts, Step 12's reset)
  is gated by a token (`PRESENTER_TOKEN`). Keep it to yourself; it is off the audience path.
- The **separately-authenticated reviewer** who could approve a *new* proposal live is the one
  documented prerequisite not yet wired (needs an account-level group / role-scoped login — see
  `docs/TECHNICAL_SETUP.md`). Do not fake it with a dropdown; the runbook shows the real denial.

## Step 2 — Baseline verification (once, before the room)

1. **Action:** on **Prove it**, click **Reproduce from retained artifacts**.
2. **Expected result:** both runs `MATCH`, every field to whole EUR; overall `reproducible ✓`.
3. **Pass/fail:** any `MISMATCH`/`FAILED` → stop and investigate before presenting (this is the
   integrity guarantee the whole close rests on).
4. **Scope limits:** this reproduces the two seeded runs; the rehearsal flows (Steps 7–12) add
   candidate versions but never change these retained runs.

---

## A — Discover with Genie  (screen: **Discover**)

**Step 3.**
1. **Starting state:** app open on **Discover**.
2. **Action:** read the business question aloud; point at the three state cards. If Genie is
   configured, click **Open the question in Genie** and ask the entry question there.
3. **Prompt:** *“What changed since the previous approved position, and what needs attention?”*
4. **Expected result:** three governed states — **Previous approved**, **New (now approved)**
   with a net movement, and **Outstanding**. Genie (or the view) never shows a proposal or a
   downstream dependency as approved.
5. **Talk track:** “A useful assistant makes people want to ask questions. The job of the
   platform is to make the answer trustworthy — approved is approved, a proposal is a proposal.”
6. **Why it matters:** demand for a good assistant creates demand for governed data underneath.
7. **Databricks service:** Genie + Databricks SQL over `vw_genie_position`.
8. **Pass/fail:** the three states render with distinct `position_status`.
9. **Recovery:** Genie not configured → present the three cards on screen and say the native
   link is a setup step (it is documented, not faked). Never relabel the agent as Genie.
10. **Scope limits:** one cohort (AY2023 Commercial Motor); the view is read-only.

## B — The business consequence  (screen: **The decision**)

**Step 4.**
1. **Starting state:** click **See the business consequence →** (or nav **The decision**).
2. **Action:** let the hero numbers count up; click along the ripple.
3. **Prompt:** none.
4. **Expected result:** **+€2.0m → +€2.2m gross → +€1.76m net**, then the green banner:
   **€2.0m already booked, only €0.2m to post.**
5. **Talk track:** “One claim change. A spreadsheet fixes one cell; here the same change ripples
   across reserve, reinsurance and finance — and the platform stops a double count.”
6. **Why it matters:** the connected decision, not the single cell, is the product.
7. **Databricks service:** Databricks Apps + Unity Catalog (live-computed by the shared engine).
8. **Pass/fail:** hero tiles animate to 2.0 / 2.2 / 1.76; residual banner shows €0.2m.
9. **Recovery:** numbers blank → warehouse cold; wait and reload. Never read numbers off a slide.
10. **Scope limits:** the capital tile says “dependency identified”, not a figure (honest).

## C — Investigate with the agent  (screen: **Investigate**)

**Step 5.**
1. **Starting state:** nav **Investigate (agent)**.
2. **Action:** click a suggested prompt; optionally ask a follow-up.
3. **Prompt:** *“Explain what changed and what evidence supports it.”* then *“Why is the proposed
   finance adjustment smaller than the reserve movement?”* then *“Which conclusions are facts,
   and which still require judgement?”*
4. **Expected result:** a grounded answer citing the same figures, separating FACT from
   HYPOTHESIS, with a `served by` badge and a green `trace <id>` badge (the call was logged).
5. **Talk track:** “Real Claude, on the Foundation Model API, grounded on the live numbers.
   It explains and compares — it cannot approve, publish or change data.”
6. **Why it matters:** the assistant is genuinely useful *and* bounded and audited.
7. **Databricks service:** Foundation Model API; trace to `7_gov_ai_trace`.
8. **Pass/fail:** an answer appears with a `trace` badge. If the badge is red (“trace NOT
   persisted”), say so — evidence would be incomplete; do not claim it was logged.
9. **Recovery:** model outage → the panel shows an honest error; move on (financial path stands).
10. **Scope limits:** read-only Q&A; it has no workflow-execution tools (do not imply otherwise).

## D — A real data-quality block  (screen: **Data quality**)

**Step 6.**
1. **Starting state:** nav **Data quality**; gate shows **RELEASED**.
2. **Action:** open **Presenter controls**, enter the token, click **1 · Introduce source
   defect**; the screen reloads. Then click **2 · Correct & revalidate**.
3. **Prompt:** none.
4. **Expected result:** after (1) the gate flips to **BLOCKED** with a failing critical check on
   a new candidate input version, and **create proposal** is refused (`GATE_BLOCKED`); after (2)
   the gate returns to **RELEASED** on a *new* candidate version. The previous approved position
   is untouched throughout.
5. **Talk track:** “Before any number, the data has to be trustworthy. A broken feed blocks the
   new run at the backend — and a PASS on the old version does not carry to the new one.”
6. **Why it matters:** partial or broken work can never show a green ‘complete’.
7. **Databricks service:** Unity Catalog + Delta (`1_raw_dq_check`, `0_cfg_scenario_state`).
8. **Pass/fail:** gate BLOCKED after (1), RELEASED after (2); the approved position never changes.
9. **Recovery:** if the token is wrong the control returns `unauthorised` — re-enter it. If you
   skip this step, run **Correct & revalidate** afterwards to leave the scenario clean.
10. **Scope limits:** the defect is a controlled, scenario-scoped flag, not a live feed break.

## E — Controlled judgement & approval  (screens: **Judgement**, **Approval**)

**Step 7 (judgement).**
1. **Starting state:** nav **Judgement**.
2. **Action:** move the what-if slider; note the ultimate move live. In **Presenter controls**,
   click **Create proposal (preparer)** and copy the returned `proposal_id`.
3. **Prompt:** none.
4. **Expected result:** the slider recomputes live; a new `PROPOSED` proposal is created, bound
   to the current input version + assumption fingerprint + calc version.
5. **Talk track:** “This is the actuary’s bench. The selection is a judgement, shown honestly
   against the empirical diagnostics. The preparer proposes — they do not approve.”
6. **Why it matters:** the proposal is bound to an exact version, so staleness is detectable.
7. **Databricks service:** Delta tables + the shared engine; proposal in `6_gov_proposal`.
8. **Pass/fail:** a `proposal_id` is returned (`PROP-REH-…`).
9. **Recovery:** if create is refused `GATE_BLOCKED`, run Step 6’s **Correct & revalidate** first.
10. **Scope limits:** the slider does not persist; only **Create proposal** writes.

**Step 8 (approval + separation of duties).**
1. **Starting state:** nav **Approval**; paste the `proposal_id` into Presenter controls.
2. **Action:** click **Self-approve (preparer)**, then **Approve as chief actuary**.
3. **Prompt:** none.
4. **Expected result:** self-approve is refused **SELF_APPROVAL**; the reviewer path passes all
   pre-conditions then is refused **REQUIRES_REVIEWER_PRINCIPAL** — the app identity is denied
   the write by Unity Catalog (no fabricated approval).
5. **Talk track:** “Separation of duties is enforced in the backend, not a dropdown. The
   preparer can’t approve their own; and the app itself has no right to write an approval.”
6. **Why it matters:** authority is a data-tier control, not a UI convention.
7. **Databricks service:** Unity Catalog (approval write denied) + Delta (`6_gov_proposal`).
8. **Pass/fail:** the two refusals appear with those exact codes.
9. **Recovery:** if you want to show a *successful* approval, that requires the separately-
   authenticated reviewer principal — currently the documented prerequisite; present the seeded
   approved decision on this screen instead and say the live approve step is pending that role.
10. **Scope limits:** the seeded `APPROVED` decision was written by the reviewer role at deploy;
    the live approve-through-the-app path is intentionally not faked.

**Step 9 (stale proposal — optional).**
1. **Action:** click **Advance version (make stale)**, then **Approve as chief actuary** again.
2. **Expected result:** refused **STALE_PROPOSAL** (input version/assumptions moved since it was
   created). 3–10 as Step 8; **scope:** run Step 12 reset afterwards to return to baseline.

## F — Downstream consequences  (screen: **Downstream**)

**Step 10.**
1. **Starting state:** nav **Downstream**.
2. **Action:** show the initial-vs-corrected table, the revision bridge, the four numbers, then
   the hand-off table.
3. **Prompt:** none.
4. **Expected result:** the four numbers kept distinct (**2.4 / 2.2 / 1.76 / 0.2**); each
   hand-off is **DELIVERED** with a versioned, idempotent id, and its **result** is
   **AWAITING RECALCULATION** (or MAPPING UNRESOLVED) — no invented statutory figure.
5. **Talk track:** “The consequence is routed downstream honestly: the inputs are delivered with
   a versioned, idempotent hand-off; the capital and IFRS 17 results are awaiting recalculation.”
6. **Why it matters:** connected ≠ fabricated — the platform is honest about what it does not run.
7. **Databricks service:** Delta (`6_gov_downstream_handoff`).
8. **Pass/fail:** delivery states DELIVERED; result states not “complete”; nothing marked posted.
9. **Recovery:** none needed (read-only).
10. **Scope limits:** no capital / IFRS 17 model runs here by design; the finance journal is
    **GENERATED, NOT POSTED**.

## G — Prove the decision  (screen: **Prove it**)

**Step 11.**
1. **Starting state:** nav **Prove it**.
2. **Action:** click **Reproduce from retained artifacts**. Read the lineage chain and the
   committee memo. Optionally, in Presenter controls, click **Advance to a newer version** then
   **Reproduce the approved run** to show reproduction survives a moved current state.
3. **Prompt:** none.
4. **Expected result:** every retained field `MATCH` to whole EUR; lineage traces executive
   amount → human decision → selection → method → triangle → population → source; the committee
   memo renders from the approved run’s retained artifacts.
5. **Talk track:** “Months later, you can prove it. We re-run the pinned calculation on the
   retained inputs — not today’s tables — and every material number matches to the euro.”
6. **Why it matters:** reproducibility and lineage are what make the decision defensible.
7. **Databricks service:** Delta (`7_gov_run_manifest`) + append-only audit; MLflow where
   implemented.
8. **Pass/fail:** `reproducible ✓`; committee memo `available`. If no approved decision exists,
   the memo honestly shows “not available” — that is correct, not a bug.
9. **Recovery:** a `FAILED`/`MISMATCH` is a real failure — do not talk over it; stop and diagnose.
10. **Scope limits:** reproduction covers the two retained runs; the newer candidate versions are
    not separately retained runs.

## H — Back to the business question & close  (screen: **Close**)

**Step 12.**
1. **Starting state:** nav **Close**.
2. **Action:** show the updated approved position and outstanding work; walk the four expansion
   cards; land on the concrete next step. Then, in Presenter controls, click **Rehearsal reset
   (preserve evidence)** to leave the scenario clean for the next run.
3. **Prompt:** none.
4. **Expected result:** the expansion view (initial workload → shared foundation → expansion →
   repeatability), each naming the additional workloads; then the reset confirms rehearsal state
   cleared with evidence preserved.
5. **Talk track:** “AI made the task easier. Operating the decision across the business is the
   opportunity — one workload becomes an estate, and it is repeatable across accounts.”
6. **Why it matters:** the expanding Databricks footprint is the commercial thesis.
7. **Databricks service:** the whole platform (each named by the result it produced).
8. **Pass/fail:** reset returns `ok` with evidence preserved.
9. **Recovery:** if reset is refused, check the token; the retained runs/audit are never touched.
10. **Scope limits:** no revenue, consumption, savings or market-size numbers are asserted.

---

## Optional practitioner drill-downs
- **Judgement:** the incurred triangle and the empirical-vs-selected diagnostic (1.19 vs 1.20).
- **Downstream:** the per-method response table (why the selection is a judgement).
- **Prove it:** the full retained run manifests and the governance audit log.

## Safe restart
Run **Rehearsal reset** (Step 12) — or `POST /api/presenter/rehearsal-reset?token=…`. It clears
rehearsal proposals and the defect flag and returns the candidate to the approved version.
**It never drops the schema and never deletes retained runs, audit, the approved decision or the
evidence archive.** A full rebuild (new isolated instance) is the deploy in `docs/TECHNICAL_SETUP.md`.

## Failure recovery quick table
| Symptom | Likely cause | Recovery |
|---|---|---|
| Hero numbers blank | warehouse cold | wait ~1 min, reload; warm before presenting |
| Agent error panel | model endpoint | say so; financial path unaffected; use trace history |
| `trace NOT persisted` badge | app SP lacks MODIFY on trace | note it honestly; fix grant (setup doc) |
| Gate stuck BLOCKED | defect left active | Step 6 **Correct & revalidate** |
| Genie step FAIL | space not created | present the three cards; setup is documented |
| Presenter action `unauthorised` | wrong token | re-enter `PRESENTER_TOKEN` |

## Recorded fallback
None supplied. If the workspace is unreachable, present `docs/EXEC_BRIEFING.md` and the
screenshots in `docs/`; state clearly that it is a recorded/still fallback, not a live run.

## Commercial close (say it plainly)
“One €2m claim correction became a governed, reproducible, connected decision — reserve,
reinsurance, finance and the downstream hand-off — with authority enforced at the data tier and
evidence you can reproduce to the euro. That is the workload that expands into an estate, and
Bricksurance makes it repeatable across accounts. The next step is to package it as a pilot.”
