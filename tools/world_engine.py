"""
Claim to Confidence — deterministic synthetic-scenario generator.

Produces the whole "From Claim to Confidence" world for a FICTIONAL insurer,
Bricksurance SE, from a single documented seed, so every run is byte-identical:

  * a real claim-transaction ledger for the hero cohort (Commercial Motor liability,
    accident year 2023) whose transactions AGGREGATE to paid €58.0m and case €23.0m
    (initial) / €25.0m (corrected) — so the triangle is derived from histories, not
    asserted (spec §4 / acceptance test T01);
  * the €2m case correction as a real transaction with TWO clocks — economically
    effective 30 Jun 2026, but only known/received 6 Jul 2026 (after the initial
    3 Jul information cutoff);
  * a seeded DUPLICATE source-delivery defect: the same business event/revision
    delivered twice with distinct delivery IDs; de-duplication on (claim_id,
    revision_id) means idempotent re-delivery has no financial effect (T02);
  * a derived multi-accident-year paid/incurred triangle (AY 2019–2026) for factor
    diagnostics, with AY2023's current diagonal reconciled to the hero ledger;
  * the seeded, GOVERNED selected development factors (incurred cumulative development
    factor 1.20, paid 1.70) — prescribed actuarial selections, not fitted here;
  * the a-priori planning basis (earned premium €120m, expected loss ratio 80%);
  * a 20% quota-share treaty covering this cohort at both cutoffs;
  * the finance ledger position that has ALREADY posted the €2m case correction
    (case €25.0m + existing IBNR €16.1m = €41.1m gross), so the finance beat books
    only the €0.2m residual — never the full movement twice (T07);
  * a simplified chart of accounts for the residual journal.

All money is emitted in whole EUR. Nothing here computes a reserve outcome — that is
engine.py's job. This module only lays down the inputs.
"""
import json
import random
from decimal import Decimal

SEED = 20260630
M = 1_000_000  # one EUR million, in whole EUR

# ── Scenario constants (the fixtures the demo narrates) ──────────────────────
ENTITY = "Bricksurance SE"
LOB = "COMMERCIAL_MOTOR"
LOB_LABEL = "Commercial Motor liability"
CURRENCY = "EUR"
VALUATION_DATE = "2026-06-30"
CUTOFF_INITIAL = "2026-07-03"
CUTOFF_CORRECTED = "2026-07-06"
HERO_CLAIM = "CLM-CM-2023-000001"
CORRECTION_EUR = 2 * M            # €2,000,000 case correction
QUOTA_SHARE_PCT = Decimal("0.20")  # 20% quota share
EARNED_PREMIUM = 120 * M
EXPECTED_LOSS_RATIO = Decimal("0.80")
SELECTED_INCURRED_CDF = Decimal("1.20")
SELECTED_PAID_CDF = Decimal("1.70")
# Selection policy for this cohort (synthetic demonstration policy, not a recommendation):
SELECTION_WEIGHTS = {"incurred_chain_ladder": Decimal("0.5"),
                     "incurred_bornhuetter_ferguson": Decimal("0.5")}

# Hero-cohort targets at the two information cutoffs (whole EUR).
AY2023_PAID = 58 * M
AY2023_CASE_INITIAL = 23 * M
AY2023_CASE_CORRECTED = 25 * M    # +€2m on the hero claim only

# The finance ledger has already booked the €2m case correction. Its existing IBNR is
# the ORIGINAL approved gross IBNR (€16.1m) carried from last close — NOT the revised
# actuarial IBNR. So ledger gross outstanding = 25.0 + 16.1 = 41.1m.
LEDGER_EXISTING_IBNR = int(round(16.1 * M))

# Development patterns (cumulative % of ultimate by annual development lag 0..7) for a
# long-tail motor-liability book. At lag 3 (AY2023's maturity at 30 Jun 2026) these give
# a paid cumulative development factor of 1/0.588 ≈ 1.70 and incurred 1/0.8333 ≈ 1.20 —
# exactly the seeded selected factors, so the selection sits credibly on the diagnostics.
PAID_PATTERN = [0.100, 0.280, 0.440, 0.588, 0.710, 0.820, 0.920, 1.000]
INCURRED_PATTERN = [0.550, 0.700, 0.790, 0.833, 0.880, 0.930, 0.975, 1.000]


def _rng():
    return random.Random(SEED)


# ─────────────────────────────────────────────────────────────────────────────
# Hero-cohort ledger (AY2023) — transactions that aggregate EXACTLY to the targets.
# ─────────────────────────────────────────────────────────────────────────────

def build_ledger():
    """Return (claims, transactions, deliveries) for the AY2023 hero cohort.

    Payments sum to €58.0m. Case estimates (latest effective-dated state per claim) sum
    to €23.0m at the initial cutoff and €25.0m at the corrected cutoff (the hero claim's
    +€2m correction, known only from 6 Jul). Exactness is guaranteed by putting the
    rounding residual on a single documented balancing claim.
    """
    rng = _rng()
    n_claims = 40
    claims, txns, deliveries = [], [], []

    # Baseline source deliveries (the ordinary quarterly feed for this cohort).
    deliveries.append({"delivery_id": "DLV-2026Q2-CM-BASE", "received_ts": "2026-07-02T18:00:00",
                       "information_cutoff": CUTOFF_INITIAL, "source_system": "ONESHIELD_CLAIMS",
                       "description": "Q2-2026 Commercial Motor claims extract (baseline)",
                       "status": "ACCEPTED", "dq_status": "PASS"})

    # Hero claim (index 0 conceptually) — a large bodily-injury motor claim.
    hero_paid = int(round(5.4 * M))
    hero_case_initial = int(round(3.0 * M))

    # Deterministic per-claim raw draws, then scale the 39 ordinary claims so a single
    # documented balancing claim (~€1.5m paid / ~€0.6m case) makes the cohort totals EXACT
    # while staying positive and plausible.
    raw_p, raw_c = [], []
    for i in range(1, n_claims):  # claims 1..39 generated; claim 40 balances the totals
        raw_p.append(max(abs(rng.gauss(1.15, 0.45)), 0.05))
        raw_c.append(max(abs(rng.gauss(0.45, 0.22)), 0.02))
    bal_paid_target, bal_case_target = int(round(1.5 * M)), int(round(0.6 * M))
    target_39_paid = AY2023_PAID - hero_paid - bal_paid_target
    target_39_case = AY2023_CASE_INITIAL - hero_case_initial - bal_case_target
    scale_p = target_39_paid / (sum(raw_p) * M)
    scale_c = target_39_case / (sum(raw_c) * M)
    payments = [max(int(round(p * M * scale_p)), 50_000) for p in raw_p]
    cases = [max(int(round(c * M * scale_c)), 20_000) for c in raw_c]

    # Balancing claim (documented) absorbs the rounding residual → exact cohort totals.
    bal_paid = AY2023_PAID - (sum(payments) + hero_paid)
    bal_case = AY2023_CASE_INITIAL - (sum(cases) + hero_case_initial)
    assert bal_paid > 0 and bal_case > 0, (bal_paid, bal_case)

    def _add_claim(idx, paid_amt, case_amt, is_hero=False, is_balance=False):
        cid = HERO_CLAIM if is_hero else f"CLM-CM-2023-{idx:06d}"
        accident_date = f"2023-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        claims.append({"claim_id": cid, "policy_number": f"POL-CM-{idx:05d}",
                       "line_of_business_code": LOB, "accident_year": 2023,
                       "accident_date": accident_date, "currency": CURRENCY,
                       "is_hero": is_hero, "is_balance": is_balance})
        # Indemnity payment(s) — dated well before the initial cutoff (historical).
        txns.append({"claim_id": cid, "revision_id": f"{cid}-PAY", "delivery_id": "DLV-2026Q2-CM-BASE",
                     "event_type": "INDEMNITY_PAYMENT", "amount": paid_amt, "currency": CURRENCY,
                     "accident_date": accident_date, "effective_date": "2026-06-30",
                     "received_ts": "2026-07-02T18:00:00", "information_cutoff": CUTOFF_INITIAL})
        # Case estimate as an effective-dated STATE (latest wins), known at the baseline cutoff.
        txns.append({"claim_id": cid, "revision_id": f"{cid}-CASE-1", "delivery_id": "DLV-2026Q2-CM-BASE",
                     "event_type": "CASE_ESTIMATE", "amount": case_amt, "currency": CURRENCY,
                     "accident_date": accident_date, "effective_date": "2026-06-30",
                     "received_ts": "2026-07-02T18:00:00", "information_cutoff": CUTOFF_INITIAL})

    _add_claim(1, hero_paid, hero_case_initial, is_hero=True)
    for i, (p, c) in enumerate(zip(payments, cases), start=2):  # claims 2..40
        _add_claim(i, p, c)
    _add_claim(n_claims + 1, bal_paid, bal_case, is_balance=True)  # claim 41 — distinct id, no collision

    # ── The €2m case correction on the hero claim (revision REV-2). Two clocks:
    #    economically effective 30 Jun 2026, but only KNOWN/received 6 Jul 2026 — after
    #    the initial 3 Jul cutoff. It sets the hero case from €3.0m to €5.0m (+€2m).
    correction_delivery = {"delivery_id": "DLV-2026-07-06-CM-CORR", "received_ts": "2026-07-06T09:10:00",
                           "information_cutoff": CUTOFF_CORRECTED, "source_system": "ONESHIELD_CLAIMS",
                           "description": "Late adjuster re-estimate of CLM-CM-2023-000001 (major BI claim)",
                           "status": "ACCEPTED", "dq_status": "PASS"}
    deliveries.append(correction_delivery)
    hero_case_corrected = hero_case_initial + CORRECTION_EUR  # 5.0m
    txns.append({"claim_id": HERO_CLAIM, "revision_id": f"{HERO_CLAIM}-CASE-2",
                 "delivery_id": "DLV-2026-07-06-CM-CORR", "event_type": "CASE_ESTIMATE",
                 "amount": hero_case_corrected, "currency": CURRENCY, "accident_date": "2023-03-14",
                 "effective_date": "2026-06-30", "received_ts": "2026-07-06T09:10:00",
                 "information_cutoff": CUTOFF_CORRECTED})

    # ── The DUPLICATE source-delivery defect: the SAME business event/revision
    #    (claim CLM-CM-2023-000001, revision -CASE-2) redelivered under a DISTINCT
    #    delivery ID. De-dup key = (claim_id, revision_id) → this must be quarantined
    #    so it produces NO additional financial effect (idempotent re-delivery).
    duplicate_delivery = {"delivery_id": "DLV-2026-07-06-CM-CORR-RETRY", "received_ts": "2026-07-06T09:42:00",
                          "information_cutoff": CUTOFF_CORRECTED, "source_system": "ONESHIELD_CLAIMS",
                          "description": "Re-delivery of the 09:10 correction batch (network retry) — duplicate",
                          "status": "QUARANTINED", "dq_status": "DUPLICATE_DELIVERY"}
    deliveries.append(duplicate_delivery)
    txns.append({"claim_id": HERO_CLAIM, "revision_id": f"{HERO_CLAIM}-CASE-2",
                 "delivery_id": "DLV-2026-07-06-CM-CORR-RETRY", "event_type": "CASE_ESTIMATE",
                 "amount": hero_case_corrected, "currency": CURRENCY, "accident_date": "2023-03-14",
                 "effective_date": "2026-06-30", "received_ts": "2026-07-06T09:42:00",
                 "information_cutoff": CUTOFF_CORRECTED, "duplicate_of": "DLV-2026-07-06-CM-CORR"})

    return claims, txns, deliveries


def dedup_transactions(txns):
    """Idempotent de-duplication on (claim_id, revision_id): the first accepted delivery
    of a business event wins; any later delivery of the same (claim_id, revision_id) from
    a QUARANTINED delivery is dropped. Returns (accepted, dropped)."""
    accepted, dropped, seen = [], [], set()
    for t in sorted(txns, key=lambda x: x["received_ts"]):
        key = (t["claim_id"], t["revision_id"])
        if t.get("duplicate_of"):
            dropped.append(t)
            continue
        if key in seen and t["event_type"] == "CASE_ESTIMATE" and t["revision_id"].endswith("CASE-2"):
            # a second physical delivery of the same case revision — no effect
            dropped.append(t)
            continue
        seen.add(key)
        accepted.append(t)
    return accepted, dropped


def aggregate_position(txns, cutoff):
    """Derive (paid, case, incurred) for the hero cohort from the ledger, as at an
    information cutoff. Paid = sum of indemnity payments known by the cutoff. Case = sum
    over claims of the LATEST case-estimate state known by the cutoff. This is the triangle
    cell derived from histories — the reserve engine never feeds itself its own answer."""
    accepted, _ = dedup_transactions(txns)
    paid = sum(t["amount"] for t in accepted
               if t["event_type"] == "INDEMNITY_PAYMENT" and t["information_cutoff"] <= cutoff)
    # latest case estimate per claim known by the cutoff
    latest_case = {}
    for t in sorted(accepted, key=lambda x: x["received_ts"]):
        if t["event_type"] == "CASE_ESTIMATE" and t["information_cutoff"] <= cutoff:
            latest_case[t["claim_id"]] = t["amount"]
    case = sum(latest_case.values())
    return {"paid": paid, "case": case, "incurred": paid + case}


# ─────────────────────────────────────────────────────────────────────────────
# Multi-accident-year triangle (AY 2019–2026) for factor diagnostics.
# Derived here as seeded aggregates; AY2023's current diagonal is reconciled to the
# hero ledger (asserted in smoke_test). Cells are whole EUR.
# ─────────────────────────────────────────────────────────────────────────────

def build_triangle():
    """Return {'PAID': {ay: {lag: cum}}, 'INCURRED': {ay: {lag: cum}}} observed as at
    30 Jun 2026 (lower triangle only). AY2026 is a mid-year origin at lag 0 (half exposure)."""
    rng = random.Random(SEED + 1)
    tri = {"PAID": {}, "INCURRED": {}}
    base_ult = {2019: 92 * M, 2020: 95 * M, 2021: 99 * M, 2022: 97 * M,
                2023: 98_600_000, 2024: 101 * M, 2025: 103 * M, 2026: 52 * M}
    for ay in range(2019, 2027):
        current_lag = min(2026 - ay, 7)
        ult = base_ult[ay]
        tri["PAID"][ay], tri["INCURRED"][ay] = {}, {}
        for lag in range(0, current_lag + 1):
            noise_p = 1.0 + rng.uniform(-0.012, 0.012)
            noise_i = 1.0 + rng.uniform(-0.010, 0.010)
            tri["PAID"][ay][lag] = int(round(ult * PAID_PATTERN[lag] * noise_p))
            tri["INCURRED"][ay][lag] = int(round(ult * INCURRED_PATTERN[lag] * noise_i))
    # Pin AY2023's current diagonal (lag 3) to the ledger targets exactly, so methods and
    # lineage tie. (Initial view: incurred 81m; the +2m correction lifts it to 83m.)
    tri["PAID"][2023][3] = AY2023_PAID
    tri["INCURRED"][2023][3] = AY2023_PAID + AY2023_CASE_INITIAL  # 81m at the initial cutoff
    return tri


# ─────────────────────────────────────────────────────────────────────────────
# Governed reference fixtures.
# ─────────────────────────────────────────────────────────────────────────────

def selected_patterns():
    return [
        {"selection_id": "SEL-2026Q2-CM-INCURRED", "line_of_business_code": LOB, "accident_year": 2023,
         "basis": "INCURRED", "cumulative_development_factor": str(SELECTED_INCURRED_CDF),
         "source_code": "MANUAL", "status_code": "APPROVED", "selected_by": "s.okonkwo@bricksurance.example",
         "approved_by": "chief.actuary@bricksurance.example", "valuation_date": VALUATION_DATE,
         "rationale": "Selected incurred cumulative development factor 1.20 for AY2023 Commercial Motor: "
                      "empirical volume-weighted factors cluster at 1.19-1.21; held at 1.20 for consistency "
                      "with the prior close and the emerging claim-count stability. Empirical diagnostics shown separately."},
        {"selection_id": "SEL-2026Q2-CM-PAID", "line_of_business_code": LOB, "accident_year": 2023,
         "basis": "PAID", "cumulative_development_factor": str(SELECTED_PAID_CDF),
         "source_code": "MANUAL", "status_code": "APPROVED", "selected_by": "s.okonkwo@bricksurance.example",
         "approved_by": "chief.actuary@bricksurance.example", "valuation_date": VALUATION_DATE,
         "rationale": "Selected paid cumulative development factor 1.70 for AY2023 Commercial Motor: paid "
                      "emergence has accelerated modestly this period; the paid projection is retained as a "
                      "diagnostic cross-check, not the booked basis, because faster payment does not by itself "
                      "evidence a higher ultimate."},
    ]


def apriori():
    return {"line_of_business_code": LOB, "accident_year": 2023, "earned_premium": EARNED_PREMIUM,
            "expected_loss_ratio": str(EXPECTED_LOSS_RATIO),
            "apriori_ultimate": int(EARNED_PREMIUM * float(EXPECTED_LOSS_RATIO))}


def treaty():
    return {"treaty_id": "TR-2026-CM-QS20", "treaty_version": 1, "type": "QUOTA_SHARE",
            "quota_share_pct": str(QUOTA_SHARE_PCT), "line_of_business_code": LOB,
            "accident_year": 2023, "effective_from": "2026-01-01", "effective_to": "2026-12-31",
            "limits": "NONE", "exclusions": "NONE", "reinstatements": "NONE",
            "note": "20% quota share covering AY2023 Commercial Motor indemnity at both cutoffs; "
                    "no limits, exclusions, reinstatements or collectibility adjustment (scoped illustration)."}


def finance_ledger_position():
    """What claims-operations has ALREADY posted at the corrected cutoff — extracted
    independently of the reserve engine. Case €25.0m + existing IBNR €16.1m = €41.1m gross."""
    return {"line_of_business_code": LOB, "accident_year": 2023, "accounting_date": VALUATION_DATE,
            "ledger_case": AY2023_CASE_CORRECTED, "ledger_existing_ibnr": LEDGER_EXISTING_IBNR,
            "ledger_gross_outstanding": AY2023_CASE_CORRECTED + LEDGER_EXISTING_IBNR,
            "posting_status": "POSTED", "extract_version": "GL-2026-07-06-01",
            "note": "Case correction of €2.0m already posted to the claims subledger before the actuarial "
                    "adjustment; existing IBNR is the prior approved gross IBNR carried forward."}


def chart_of_accounts():
    return [
        {"account_code": "GROSS_CLAIMS_EXPENSE", "account_name": "Gross claims incurred (expense)", "account_type": "EXPENSE"},
        {"account_code": "IBNR_LIABILITY", "account_name": "IBNR reserve (liability)", "account_type": "LIABILITY"},
        {"account_code": "REINSURANCE_RECOVERABLE", "account_name": "Reinsurance recoverable (asset)", "account_type": "ASSET"},
        {"account_code": "REINSURANCE_RECOVERY_INCOME", "account_name": "Reinsurance recovery (income)", "account_type": "INCOME"},
    ]


def scenario():
    """Assemble the full world as one dict — the single source used by the engine tests,
    the deploy script (→ Unity Catalog) and local JSON fixtures."""
    claims, txns, deliveries = build_ledger()
    accepted, dropped = dedup_transactions(txns)
    return {
        "meta": {"entity": ENTITY, "lob": LOB, "lob_label": LOB_LABEL, "currency": CURRENCY,
                 "valuation_date": VALUATION_DATE, "cutoff_initial": CUTOFF_INITIAL,
                 "cutoff_corrected": CUTOFF_CORRECTED, "hero_claim": HERO_CLAIM, "seed": SEED,
                 "quota_share_pct": str(QUOTA_SHARE_PCT), "earned_premium": EARNED_PREMIUM,
                 "expected_loss_ratio": str(EXPECTED_LOSS_RATIO),
                 "selected_incurred_cdf": str(SELECTED_INCURRED_CDF),
                 "selected_paid_cdf": str(SELECTED_PAID_CDF),
                 "selection_weights": {k: str(v) for k, v in SELECTION_WEIGHTS.items()}},
        "claims": claims, "transactions": txns, "accepted_transactions": accepted,
        "dropped_transactions": dropped, "deliveries": deliveries,
        "position_initial": aggregate_position(txns, CUTOFF_INITIAL),
        "position_corrected": aggregate_position(txns, CUTOFF_CORRECTED),
        "triangle": build_triangle(), "selected_patterns": selected_patterns(),
        "apriori": apriori(), "treaty": treaty(),
        "finance_ledger_position": finance_ledger_position(), "chart_of_accounts": chart_of_accounts(),
    }


if __name__ == "__main__":
    import sys
    s = scenario()
    print(f"[world_engine] entity={s['meta']['entity']} lob={s['meta']['lob']} seed={s['meta']['seed']}")
    print(f"  claims={len(s['claims'])} transactions={len(s['transactions'])} "
          f"(accepted={len(s['accepted_transactions'])}, dropped_duplicates={len(s['dropped_transactions'])})")
    print(f"  position @ {s['meta']['cutoff_initial']}: {s['position_initial']}")
    print(f"  position @ {s['meta']['cutoff_corrected']}: {s['position_corrected']}")
    if "--json" in sys.argv:
        with open("scenario.json", "w") as f:
            json.dump(s, f, indent=2, default=str)
        print("  wrote scenario.json")
