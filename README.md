# From Claim to Confidence

**A connected, governed reserving journey for Bricksurance SE (a fictional insurer, synthetic data).**

One €2 million correction to a single motor claim, traced — with enforced authority and a
full audit trail — through the reserve, the reinsurance treaty, the finance ledger and the
capital hand-off. Built to answer the question a spreadsheet cannot: *when a claim changes,
can you trust the number that comes out the other end, and can you prove how you got there?*

> **Hero result (synthetic oracle):** €2.0m case correction → **+€2.2m** selected gross
> outstanding → **+€1.76m** net after a 20% quota-share treaty. Because €2.0m is already
> booked in finance, only the **€0.2m** residual is proposed for posting — never double-counted.

This is an **isolated scenario instance** forked from the proven Reserving Workbench engine so
it never touches the live Hiscox demo. Its executive screens are built to port into the Group
Control Tower (the estate front door) as a promoted journey.

## What is real

- **Runs for real on Databricks.** 14 Unity Catalog tables in the isolated schema
  `lr_dev_aws_us_catalog.claim_to_confidence`; the app reads them live and computes every
  business number through a pure engine that acceptance tests prove to the cent.
- **No browser-side reserve maths, no fabricated results.** The engine derives methods,
  selection, reinsurance and the finance journal from stored inputs. `tools/smoke_test.py`
  holds the independent §5 oracle and checks the engine reproduces it (43/43 checks, to the cent).
- **The triangle is derived from the claim ledger** (no duplicated business data); AY2023's
  current diagonal reconciles to the ledger aggregate.

## The six screens

| Screen | What it shows |
|---|---|
| **A · The decision** | Executive hero: the €2.0m → +€2.2m gross → +€1.76m net ripple across claim → reserve → reinsurance → finance → capital, and the double-count-prevention reveal. |
| **B · Data readiness** | Source deliveries, the quarantined **duplicate delivery**, control totals at both information cutoffs, quality gate. |
| **C · Practitioner** | The triangle, empirical-vs-selected development factors, the four method indications, and a live what-if on the selection weight. |
| **D · Change impact** | The two cutoffs compared, how each method responds, the revision bridge (posted vs residual), and the four numbers kept distinct (2.4 / 2.2 / 1.76 / 0.2). |
| **E · Review & approval** | The exact proposal, the authority matrix the backend enforces, the balanced residual journal, and a negative test (agent identity denied). |
| **F · Decision & evidence** | Retained run manifests, deterministic **"reproduce this calculation"**, and the append-only audit log. |

## Layout

```
tools/     engine.py (pure calc), world_engine.py (deterministic scenario),
           smoke_test.py (acceptance oracle, 43/43), deploy_databricks.py (→ Unity Catalog)
app/       FastAPI backend (app.py + server/) + single-file SPA (dist/index.html)
docs/      exec briefing, oracle, acceptance-test map, demo run, build log, run manifests
```

## Reproduce / redeploy

```bash
# 1. prove the oracle headless (no Databricks needed)
python3 tools/smoke_test.py

# 2. (re)deploy the scenario tables to Unity Catalog — idempotent, resets the instance
uv run --native-tls --with databricks-sdk tools/deploy_databricks.py --profile DEV

# 3. deploy the app (see docs/OVERNIGHT_BUILD_LOG.md for the create/import/grant/deploy steps)
```

## Target environment

DEV `fevm-lr-dev-aws-us` (profile DEV) · catalog `lr_dev_aws_us_catalog` · schema
`claim_to_confidence` · warehouse `a3b61648ea4809e3` (Serverless). Portable to FINS by
overriding the catalog. Public repo: `wryszka/claim-to-confidence`.

See **docs/ORACLE.md** for the verified financial oracle and **docs/OVERNIGHT_BUILD_LOG.md**
for what is built, tested and still open.
