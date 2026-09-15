# Operator manual — "From Claim to Confidence" (run it yourself)

This manual is for **someone who has never seen this demo before**. Follow it top to bottom.
No coding is required to *run* it. Every place you need to click is a real link below. It takes
about 20 minutes to present, plus a 10-minute check the first time.

If you read only one paragraph, read this:

> **What this demo is.** A fictional insurer, *Bricksurance SE*, has to change one big motor
> insurance claim by **€2 million**. This demo shows that single change flowing through the whole
> business — the reserve, the reinsurance, the finance ledger, and the downstream reporting — on
> Databricks, with the controls (data quality, who's allowed to approve, and a full audit trail)
> enforced for real, not faked. The message: *AI makes the individual task easier; the platform is
> what lets you operate the resulting decision safely across the business.*
>
> One word to know: a **reserve** is *an insurer's estimate of money it still expects to pay for
> claims that have already happened.*

---

## 1. The assets (your clickable links)

You will be asked to sign in with your Databricks account the first time you open each one.

| What | Link |
|---|---|
| **The demo app** (this is what you present) | https://claim-to-confidence-7474656169654171.aws.databricksapps.com |
| Genie space (the plain-English question box) | https://fevm-lr-dev-aws-us.cloud.databricks.com/genie/rooms/01f1b0f57ec01b5885ad6f7cf2cd75a4 |
| The governed data (Catalog Explorer) | https://fevm-lr-dev-aws-us.cloud.databricks.com/explore/data/lr_dev_aws_us_catalog/claim_to_confidence |
| The approvals table (`6_gov_decision`) | https://fevm-lr-dev-aws-us.cloud.databricks.com/explore/data/lr_dev_aws_us_catalog/claim_to_confidence/6_gov_decision |
| The AI activity log (`7_gov_ai_trace`) | https://fevm-lr-dev-aws-us.cloud.databricks.com/explore/data/lr_dev_aws_us_catalog/claim_to_confidence/7_gov_ai_trace |
| The evidence archive (kept when the demo resets) | https://fevm-lr-dev-aws-us.cloud.databricks.com/explore/data/lr_dev_aws_us_catalog/claim_to_confidence_archive |
| The SQL warehouse (the engine that runs queries) | https://fevm-lr-dev-aws-us.cloud.databricks.com/sql/warehouses/a3b61648ea4809e3 |
| The AI model (Claude, via Databricks) | https://fevm-lr-dev-aws-us.cloud.databricks.com/ml/endpoints/databricks-claude-sonnet-5 |
| App admin page (status, restart, logs) | https://fevm-lr-dev-aws-us.cloud.databricks.com/apps/claim-to-confidence |

The app has **nine screens** down the left-hand side, lettered **A–I**. You present them in that
order. That's the whole flow.

---

## 2. Before you start (do this once, ~10 minutes before)

1. **Open the demo app** (first link above) and sign in. Leave it open a minute — the first click
   "wakes up" the engine, so the numbers appear instantly when you present.
2. **Confirm it's healthy.** In the app, the numbers on screen **B** should animate to
   **+€2.0m → +€2.2m → +€1.76m**. If they're blank, wait 60 seconds and reload (the engine was
   asleep).
3. **Know the presenter password.** A few steps use hidden "Presenter controls." The password is
   set by whoever deployed the app (default word: `present`). You type it once into the box inside
   the grey **Presenter controls** panel on the relevant screen. The audience does not need to see
   this.
4. **(Optional, technical) One-command health check.** If you have the code checked out, run
   `python3 tools/preflight.py`. It should say `ready=true` (8 of 8). This confirms the warehouse,
   data, AI model, audit log and the approval controls are all in place. *A working web page alone
   is not proof — this check is.*

That's it. You do **not** need to deploy anything to run the demo — it is already live.
(Deploying, granting access, or rebuilding is in the separate `TECHNICAL_SETUP.md`.)

---

## 3. The run — screen by screen

For each screen: **where you are · what to click · what you'll see · what to say.** The numbers
below are the real, verified figures — if you see different numbers, see §4 (troubleshooting).

### A — Discover (start here)
- **Click:** screen **A · Discover (Genie)** in the left menu.
- **You'll see:** the business question *"What changed since the previous approved position, and
  what needs attention?"* and **three cards**: the **previous approved** position, the **new (now
  approved)** position with **+€1.76m net**, and the **outstanding** work.
- **Optional:** click **Open the question in Genie** to ask it in plain English in Databricks
  Genie. It answers from the same governed data.
- **Say:** *"A good assistant makes people want to ask questions. The platform's job is to make the
  answer trustworthy — an approved number is clearly separated from a proposal or unfinished work."*

### B — The decision (the "wow")
- **Click:** **B · The decision**.
- **You'll see:** three big numbers count up — **+€2.0m** (the claim change), **+€2.2m** (the gross
  reserve effect), **+€1.76m** (the net effect after reinsurance) — then a **green banner**:
  *€2.0m already booked, only €0.2m to post.*
- **Say:** *"One claim change. A spreadsheet fixes one cell; here the same change ripples across
  reserve, reinsurance and finance — and the platform stops us from counting the €2m twice."*

### C — Investigate (the AI assistant)
- **Click:** **C · Investigate (agent)**, then click a suggested question such as *"Why is the
  proposed finance adjustment smaller than the reserve movement?"*
- **You'll see:** a written answer that labels **FACT** vs **HYPOTHESIS**, plus a small green
  **"trace"** badge (the question was logged).
- **Say:** *"This is real Claude, grounded on the live numbers. It explains and compares — it
  cannot approve, publish or change data. And every question it's asked is recorded."*
- **Try the safety test:** in **Prompt-injection test**, click **Run injection test**. A hidden
  malicious note in the claim tries to make the assistant leak other data and rubber-stamp the
  reserve. **You'll see** the assistant **flag it and refuse**, then answer normally.

### D — Data quality (the gate)
- **Click:** **D · Data quality**. The gate reads **RELEASED**.
- **Presenter controls (type the password once):** click **1 · Introduce source defect**. The page
  reloads and the gate flips to **BLOCKED** — a broken feed cannot produce a new number. Then click
  **2 · Correct & revalidate**; the gate returns to **RELEASED**.
- **Say:** *"Before any number, the data has to be trustworthy. A broken feed blocks the new
  calculation at the backend — and importantly, an old 'pass' does not count for the new data."*

### E — Judgement (the actuary's bench)
- **Click:** **E · Judgement**. Move the **slider** and watch the ultimate number change live.
- **Presenter controls:** click **Create proposal (preparer)**. Copy the `proposal_id` it returns
  (looks like `PROP-REH-…`) — you'll paste it on the next screen.
- **Say:** *"The selection is a judgement, shown honestly against the data. The preparer proposes —
  they do not approve."*

### F — Approval (who's allowed to sign off)
- **Click:** **F · Approval**. You'll see the proposal, the approved decision, and the authority
  matrix.
- **Presenter controls:** paste the `proposal_id` from screen E, then:
  - click **Self-approve (preparer)** → refused **SELF_APPROVAL** (the preparer can't approve their
    own work).
  - click **Approve as chief actuary** → it passes the checks, then is refused
    **REQUIRES_REVIEWER_PRINCIPAL** — the app itself is **not allowed** to write an approval; only a
    separately signed-in reviewer can. *This refusal is enforced by Databricks Unity Catalog, not by
    the app pretending.*
- **Say:** *"Who may approve is enforced in the data platform, not by a dropdown. The preparer
  can't approve their own; and the app has no right to write an approval at all."*

### G — Downstream (the knock-on effects)
- **Click:** **G · Downstream**. You'll see the before/after table, the **four numbers kept
  distinct (2.4 / 2.2 / 1.76 / 0.2)**, and the hand-off table.
- **You'll see:** each hand-off to Capital and IFRS 17 is **DELIVERED** but its result is
  **AWAITING RECALCULATION** — we pass the inputs honestly and do **not** invent a capital figure.
- **Say:** *"The consequence is routed downstream honestly. We hand over the exact inputs; we don't
  fabricate the capital or accounting result."*

### H — Prove it (reproduce the decision)
- **Click:** **H · Prove it**, then **Reproduce from retained artifacts**.
- **You'll see:** every number re-computed from the **saved record** and marked **MATCH** to the
  euro; a lineage chain from the headline figure down to the source; and the committee memo.
- **Say:** *"Months later, you can prove it. We re-run the exact saved inputs — not today's data —
  and every material number matches to the euro."*

### I — Close (the business case)
- **Click:** **I · Close**. You'll see the updated position and four cards showing how this one
  workload grows into an estate.
- **Presenter controls:** click **Rehearsal reset (preserve evidence)** to leave the demo clean for
  the next person. This never deletes the saved records.
- **Say:** *"AI made the task easier. Operating the decision across the business is the
  opportunity — one workload becomes an estate, and it's repeatable across accounts."*

---

## 4. If something goes wrong

| You see… | It means… | Do this |
|---|---|---|
| Blank numbers on screen B | the engine was asleep | wait ~1 minute, reload; always warm it before presenting |
| The assistant shows an error box | the AI model is briefly unavailable | say so and move on — the money story doesn't depend on it |
| A red "trace NOT persisted" badge | the audit log couldn't be written | note it honestly; the deployer needs to re-check permissions |
| The gate is stuck on **BLOCKED** | a defect was left switched on | on screen D, click **Correct & revalidate** |
| Genie link doesn't load | you may lack access to the space | ask the deployer to share the Genie space with you |
| A presenter button says **unauthorised** | wrong presenter password | re-type it in the Presenter controls box |

If the whole workspace is unreachable, present the one-page brief `docs/EXEC_BRIEFING.md` and the
screenshots in `docs/`, and say clearly it's a fallback, not a live run.

---

## 5. What we claim — and what we don't (say these honestly if asked)

- The **money is real maths**, computed live and checked to the cent — not typed in.
- The **approval refusal is real**: the app is genuinely denied permission to approve by the data
  platform. A live *successful* approval by a separate reviewer person is the one piece still being
  wired up (it needs a separate sign-in role) — so we show the enforced refusal and the already-
  approved record, and we don't fake the "yes."
- We **do not invent** a capital or accounting (IFRS 17) figure — those are shown as "awaiting
  recalculation."
- The insurer and all data are **fictional and synthetic**. This is a demo, not a regulatory result.
- We keep it **cooperative**: this is an *Anthropic + Databricks* story (a great assistant creating
  demand for a governed platform), never a knock on spreadsheets or on Anthropic.

---

## 6. For the technical operator (not needed to present)
Setup, grants, redeploy, Genie creation and recovery are in **`docs/TECHNICAL_SETUP.md`**. The
detailed talk-track runbook is in **`docs/DEMO_RUN.md`**. The proof of every control is in
**`docs/ACCEPTANCE_TESTS.md`**. This build is **live and verified** (2026-09-15): preflight 8/8;
the full A–I sequence tested through the deployed app.
