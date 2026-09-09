"""
Claim to Confidence — the reserving/reinsurance/finance calculation engine.

This module is PURE: every function takes explicit inputs and returns typed results.
It has no database dependency, so it is unit-testable in isolation and the same code
runs behind the app (server reads Unity Catalog tables, then calls these functions).

Non-negotiable (see spec §3 "definition of real"): production handlers derive answers
independently from inputs. Nothing here returns a canned business result — every number
is computed from paid / case / selected factors / premium / loss ratio / treaty share /
the finance ledger position. The acceptance tests in smoke_test.py hold the independent
§5 oracle and check that this engine reproduces it to the cent.

All money is handled as Python Decimal in whole EUR (not millions) for exactness, and
presented in EUR millions at the edge. The demo scenario is EUR, Commercial Motor
liability, accident year 2023, valuation 30 June 2026.
"""
from decimal import Decimal, getcontext, ROUND_HALF_UP

getcontext().prec = 34  # generous precision; we round to the cent at the edge

CENT = Decimal("0.01")
MILLION = Decimal("1000000")


def _d(x) -> Decimal:
    """Coerce to Decimal without binary-float noise."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def cents(x) -> Decimal:
    """Round to the nearest cent (2 dp), half-up — the money rounding rule for this demo."""
    return _d(x).quantize(CENT, rounding=ROUND_HALF_UP)


def to_millions(x, dp=2) -> float:
    """Present a whole-EUR Decimal in EUR millions, for display/JSON only."""
    q = Decimal("1").scaleb(-dp)  # e.g. 0.01 for dp=2
    return float((_d(x) / MILLION).quantize(q, rounding=ROUND_HALF_UP))


# ─────────────────────────────────────────────────────────────────────────────
# Method engine — the four standard property & casualty reserving indications.
# All amounts in whole EUR. `incurred_cdf` / `paid_cdf` are the SELECTED cumulative
# development factors to ultimate (seeded, governed actuarial selections — NOT fitted
# here; empirical diagnostics live elsewhere and are shown separately).
# ─────────────────────────────────────────────────────────────────────────────

def reported_incurred(paid, case) -> Decimal:
    return cents(_d(paid) + _d(case))


def incurred_chain_ladder(paid, case, incurred_cdf) -> Decimal:
    """Ultimate = reported incurred × selected incurred cumulative development factor."""
    return cents(reported_incurred(paid, case) * _d(incurred_cdf))


def paid_chain_ladder(paid, paid_cdf) -> Decimal:
    """Ultimate = paid to date × selected paid cumulative development factor."""
    return cents(_d(paid) * _d(paid_cdf))


def expected_ultimate(earned_premium, expected_loss_ratio) -> Decimal:
    """A-priori expected ultimate = earned premium × expected loss ratio."""
    return cents(_d(earned_premium) * _d(expected_loss_ratio))


def incurred_bornhuetter_ferguson(paid, case, incurred_cdf, earned_premium, expected_loss_ratio) -> Decimal:
    """BF ultimate = reported incurred + expected ultimate × (1 − 1/incurred CDF).

    The BF method credibility-weights toward the a-priori for the still-undeveloped
    portion (1 − 1/CDF), and takes reported experience as-is for the developed portion.
    """
    inc = reported_incurred(paid, case)
    exp = expected_ultimate(earned_premium, expected_loss_ratio)
    unpaid_pct = Decimal(1) - (Decimal(1) / _d(incurred_cdf))
    return cents(inc + exp * unpaid_pct)


def method_indications(paid, case, incurred_cdf, paid_cdf, earned_premium, expected_loss_ratio) -> dict:
    """All four indications for one cohort at one information cutoff."""
    return {
        "reported_incurred": reported_incurred(paid, case),
        "incurred_chain_ladder": incurred_chain_ladder(paid, case, incurred_cdf),
        "paid_chain_ladder": paid_chain_ladder(paid, paid_cdf),
        "expected_ultimate": expected_ultimate(earned_premium, expected_loss_ratio),
        "incurred_bornhuetter_ferguson": incurred_bornhuetter_ferguson(
            paid, case, incurred_cdf, earned_premium, expected_loss_ratio),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Selection — the actuary's blend policy across methods, then outstanding & IBNR.
# The demo policy for this cohort is 50% incurred chain-ladder + 50% incurred BF
# (a synthetic demonstration policy, not a general recommendation). Weights are
# validated to sum to 1 and each in [0, 1]; the UI lets the actuary change them
# within these bounds and recompute — the engine is genuinely sensitive to them.
# ─────────────────────────────────────────────────────────────────────────────

def select_ultimate(indications: dict, weights: dict) -> Decimal:
    """Weighted blend of named method indications. `weights` maps method key → weight.

    Raises if weights are out of bounds or do not sum to 1 (within a tiny tolerance),
    or if a weighted method is missing — a silent renormalisation would let a bad
    selection look valid.
    """
    total = Decimal(0)
    acc = Decimal(0)
    for key, w in weights.items():
        wd = _d(w)
        if wd < 0 or wd > 1:
            raise ValueError(f"weight for {key} out of [0,1]: {w}")
        if key not in indications:
            raise KeyError(f"weighted method not in indications: {key}")
        acc += indications[key] * wd
        total += wd
    if abs(total - Decimal(1)) > Decimal("0.0001"):
        raise ValueError(f"selection weights must sum to 1, got {total}")
    return cents(acc)


def outstanding_and_ibnr(selected_ultimate, paid, case) -> dict:
    """Gross outstanding = ultimate − paid; gross IBNR = ultimate − paid − case."""
    su = _d(selected_ultimate)
    gross_os = cents(su - _d(paid))
    gross_ibnr = cents(su - _d(paid) - _d(case))
    return {"selected_ultimate": cents(su), "gross_outstanding": gross_os, "gross_ibnr": gross_ibnr}


# ─────────────────────────────────────────────────────────────────────────────
# Reinsurance — a 20% quota share on this cohort's indemnity, at both cutoffs, with
# no limits/exclusions/reinstatements/collectibility adjustment (a scoped illustration).
# Quota share is proportional, so it applies cleanly to the aggregate outstanding.
# Gross liability and reinsurance recoverable stay separately identifiable.
# ─────────────────────────────────────────────────────────────────────────────

def apply_quota_share(gross_outstanding, quota_share_pct) -> dict:
    g = _d(gross_outstanding)
    qs = _d(quota_share_pct)
    ceded = cents(g * qs)
    net = cents(g - ceded)
    return {"gross_outstanding": cents(g), "ceded_outstanding": ceded, "net_outstanding": net,
            "quota_share_pct": qs}


# ─────────────────────────────────────────────────────────────────────────────
# One full valuation of the cohort: methods → selection → outstanding → reinsurance.
# ─────────────────────────────────────────────────────────────────────────────

def value_cohort(paid, case, incurred_cdf, paid_cdf, earned_premium, expected_loss_ratio,
                 weights, quota_share_pct) -> dict:
    ind = method_indications(paid, case, incurred_cdf, paid_cdf, earned_premium, expected_loss_ratio)
    su = select_ultimate(ind, weights)
    oi = outstanding_and_ibnr(su, paid, case)
    ri = apply_quota_share(oi["gross_outstanding"], quota_share_pct)
    return {
        "inputs": {"paid": cents(paid), "case": cents(case), "incurred_cdf": _d(incurred_cdf),
                   "paid_cdf": _d(paid_cdf), "earned_premium": cents(earned_premium),
                   "expected_loss_ratio": _d(expected_loss_ratio),
                   "quota_share_pct": _d(quota_share_pct), "weights": {k: _d(v) for k, v in weights.items()}},
        "indications": ind,
        "selected_ultimate": oi["selected_ultimate"],
        "gross_outstanding": oi["gross_outstanding"],
        "gross_ibnr": oi["gross_ibnr"],
        "ceded_outstanding": ri["ceded_outstanding"],
        "net_outstanding": ri["net_outstanding"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Finance — prevent double counting. The claims ledger has ALREADY posted the €2m
# case correction before the actuarial adjustment is prepared. So finance must book
# only the residual: revised selected gross outstanding minus the position already on
# the ledger. The ledger position is extracted INDEPENDENTLY of the reserve engine
# (it is what claims-operations posted), which is the whole point of the beat.
# ─────────────────────────────────────────────────────────────────────────────

def residual_finance_adjustment(revised_gross_outstanding, ledger_case, ledger_existing_ibnr,
                                quota_share_pct) -> dict:
    """Residual to book = revised selected gross outstanding − (ledger case + ledger existing IBNR).

    Returns the gross/ceded/net residual and a balanced proposed journal (in whole EUR).
    Never books the full movement again — only what the ledger has not already captured.
    """
    revised = _d(revised_gross_outstanding)
    ledger_gross = cents(_d(ledger_case) + _d(ledger_existing_ibnr))
    residual_gross = cents(revised - ledger_gross)                       # all IBNR in this scenario
    residual_ceded = cents(residual_gross * _d(quota_share_pct))
    residual_net = cents(residual_gross - residual_ceded)
    # Balanced double-entry journal for the residual only (simplified indemnity subledger).
    journal = [
        {"account": "GROSS_CLAIMS_EXPENSE", "dr": residual_gross, "cr": Decimal("0.00")},
        {"account": "IBNR_LIABILITY", "dr": Decimal("0.00"), "cr": residual_gross},
        {"account": "REINSURANCE_RECOVERABLE", "dr": residual_ceded, "cr": Decimal("0.00")},
        {"account": "REINSURANCE_RECOVERY_INCOME", "dr": Decimal("0.00"), "cr": residual_ceded},
    ]
    total_dr = cents(sum((line["dr"] for line in journal), Decimal(0)))
    total_cr = cents(sum((line["cr"] for line in journal), Decimal(0)))
    return {
        "ledger_gross_outstanding": ledger_gross,
        "revised_gross_outstanding": cents(revised),
        "residual_gross": residual_gross,
        "residual_ceded": residual_ceded,
        "residual_net": residual_net,
        "journal": journal,
        "journal_total_dr": total_dr,
        "journal_total_cr": total_cr,
        "balanced": total_dr == total_cr,
    }


def movement_bridge(initial: dict, corrected: dict, ledger_case_correction_gross,
                    quota_share_pct) -> dict:
    """The revision bridge vs the original approved position, split into the piece already
    posted (the case correction) and the piece still to book (the additional IBNR)."""
    qs = _d(quota_share_pct)
    case_gross = cents(ledger_case_correction_gross)
    case_ceded = cents(case_gross * qs)
    case_net = cents(case_gross - case_ceded)

    total_gross = cents(corrected["gross_outstanding"] - initial["gross_outstanding"])
    total_ceded = cents(corrected["ceded_outstanding"] - initial["ceded_outstanding"])
    total_net = cents(corrected["net_outstanding"] - initial["net_outstanding"])

    addl_gross = cents(total_gross - case_gross)
    addl_ceded = cents(total_ceded - case_ceded)
    addl_net = cents(total_net - case_net)

    return {
        "case_correction_posted": {"gross": case_gross, "ceded": case_ceded, "net": case_net},
        "additional_ibnr_to_book": {"gross": addl_gross, "ceded": addl_ceded, "net": addl_net},
        "total_revision": {"gross": total_gross, "ceded": total_ceded, "net": total_net},
    }
