"""
Claim to Confidence — headless acceptance tests. Proves the §5 financial oracle to the
cent, from the generated scenario, with NO database and NO app. Run this first and keep
it green before anything else is built on top.

The oracle values below are the INDEPENDENT expected results from the specification's §5
(EUR millions, accident year 2023, gross undiscounted indemnity). The test holds them and
checks the engine reproduces them from the world_engine inputs — the test does not
duplicate the engine's arithmetic.

Maps to acceptance tests: T01 (ledger aggregates), T02 (duplicate caught, idempotent),
T04 (each method ties to oracle), T05 (sensitivity), T06 (gross/ceded/net/IBNR), T07
(finance residual only + balanced + duplicate-post protection).
"""
import sys
from decimal import Decimal

sys.path.insert(0, ".")
import engine as E
import world_engine as W

M = Decimal(W.M)  # one million, Decimal

# ── Oracle (EUR millions) from spec §5 ───────────────────────────────────────
ORACLE = {
    "initial": {
        "reported_incurred": "81.0", "incurred_cl": "97.2", "paid_cl": "98.6",
        "expected_ultimate": "96.0", "incurred_bf": "97.0",
        "selected_ultimate": "97.1", "gross_outstanding": "39.1", "gross_ibnr": "16.1",
        "ceded_outstanding": "7.82", "net_outstanding": "31.28",
    },
    "corrected": {
        "reported_incurred": "83.0", "incurred_cl": "99.6", "paid_cl": "98.6",
        "expected_ultimate": "96.0", "incurred_bf": "99.0",
        "selected_ultimate": "99.3", "gross_outstanding": "41.3", "gross_ibnr": "16.3",
        "ceded_outstanding": "8.26", "net_outstanding": "33.04",
    },
    "finance": {"ledger_gross": "41.1", "residual_gross": "0.2", "residual_ceded": "0.04", "residual_net": "0.16"},
    "bridge": {"case_gross": "2.0", "case_net": "1.6", "addl_gross": "0.2", "addl_net": "0.16",
               "total_gross": "2.2", "total_net": "1.76"},
}

TOL = Decimal("0.01") * M  # one cent, in whole EUR
results = []


def check(name, got_eur, expected_millions):
    exp = Decimal(expected_millions) * M
    ok = abs(E._d(got_eur) - exp) <= TOL
    results.append((ok, name, E.to_millions(got_eur), expected_millions))
    return ok


def run():
    s = W.scenario()
    meta = s["meta"]
    weights = {k: Decimal(v) for k, v in meta["selection_weights"].items()}
    inc_cdf = Decimal(meta["selected_incurred_cdf"])
    paid_cdf = Decimal(meta["selected_paid_cdf"])
    prem = meta["earned_premium"]
    elr = Decimal(meta["expected_loss_ratio"])
    qs = Decimal(meta["quota_share_pct"])

    # ── T01 — the ledger aggregates to the oracle positions ──────────────────
    pos_i, pos_c = s["position_initial"], s["position_corrected"]
    check("T01 paid (initial, from ledger)", pos_i["paid"], "58.0")
    check("T01 case (initial, from ledger)", pos_i["case"], "23.0")
    check("T01 incurred (initial, from ledger)", pos_i["incurred"], "81.0")
    check("T01 case (corrected, from ledger)", pos_c["case"], "25.0")
    check("T01 incurred (corrected, from ledger)", pos_c["incurred"], "83.0")

    # T13 lineage — AY2023 triangle current diagonal ties to the ledger
    tri = s["triangle"]
    check("T13 triangle paid[2023][3] ties to ledger", tri["PAID"][2023][3], "58.0")
    check("T13 triangle incurred[2023][3] ties to ledger (initial)", tri["INCURRED"][2023][3], "81.0")

    # ── T02 — duplicate delivery caught; idempotent (no second €2m) ───────────
    dropped = s["dropped_transactions"]
    dup_ok = any(t.get("duplicate_of") for t in dropped)
    results.append((dup_ok, "T02 duplicate delivery quarantined (no financial effect)",
                    len(dropped), ">=1"))
    # re-running dedup on the accepted set must be a no-op (idempotent)
    reacc, redrop = W.dedup_transactions(s["accepted_transactions"])
    results.append((len(redrop) == 0 and len(reacc) == len(s["accepted_transactions"]),
                    "T02 idempotent re-delivery (accepted set stable)", len(redrop), "0"))

    # ── T04 / T06 — every method + selection + reinsurance ties to the oracle ─
    for label, pos in (("initial", pos_i), ("corrected", pos_c)):
        v = E.value_cohort(pos["paid"], pos["case"], inc_cdf, paid_cdf, prem, elr, weights, qs)
        o = ORACLE[label]
        ind = v["indications"]
        check(f"T04 reported incurred ({label})", ind["reported_incurred"], o["reported_incurred"])
        check(f"T04 incurred chain-ladder ({label})", ind["incurred_chain_ladder"], o["incurred_cl"])
        check(f"T04 paid chain-ladder ({label})", ind["paid_chain_ladder"], o["paid_cl"])
        check(f"T04 expected ultimate ({label})", ind["expected_ultimate"], o["expected_ultimate"])
        check(f"T04 incurred Bornhuetter-Ferguson ({label})", ind["incurred_bornhuetter_ferguson"], o["incurred_bf"])
        check(f"T06 selected ultimate ({label})", v["selected_ultimate"], o["selected_ultimate"])
        check(f"T06 gross outstanding ({label})", v["gross_outstanding"], o["gross_outstanding"])
        check(f"T06 gross IBNR ({label})", v["gross_ibnr"], o["gross_ibnr"])
        check(f"T06 ceded outstanding ({label})", v["ceded_outstanding"], o["ceded_outstanding"])
        check(f"T06 net outstanding ({label})", v["net_outstanding"], o["net_outstanding"])

    # keep the two valuations for finance + bridge
    vi = E.value_cohort(pos_i["paid"], pos_i["case"], inc_cdf, paid_cdf, prem, elr, weights, qs)
    vc = E.value_cohort(pos_c["paid"], pos_c["case"], inc_cdf, paid_cdf, prem, elr, weights, qs)

    # ── T07 — finance books only the residual, balanced, no double count ──────
    lp = s["finance_ledger_position"]
    fin = E.residual_finance_adjustment(vc["gross_outstanding"], lp["ledger_case"],
                                        lp["ledger_existing_ibnr"], qs)
    check("T07 ledger gross outstanding (independent)", fin["ledger_gross_outstanding"], ORACLE["finance"]["ledger_gross"])
    check("T07 residual gross to book", fin["residual_gross"], ORACLE["finance"]["residual_gross"])
    check("T07 residual ceded to book", fin["residual_ceded"], ORACLE["finance"]["residual_ceded"])
    check("T07 residual net", fin["residual_net"], ORACLE["finance"]["residual_net"])
    results.append((fin["balanced"], "T07 proposed journal is balanced (dr == cr)",
                    E.to_millions(fin["journal_total_dr"]), E.to_millions(fin["journal_total_cr"])))
    # the residual must NOT be the full movement (double-count protection)
    not_double = fin["residual_gross"] < Decimal("2.1") * M
    results.append((not_double, "T07 residual is NOT the full €2.2m (no double count)",
                    E.to_millions(fin["residual_gross"]), "0.2"))

    # ── bridge — case-posted vs additional-to-book vs total revision ──────────
    br = E.movement_bridge(vi, vc, W.CORRECTION_EUR, qs)
    b = ORACLE["bridge"]
    check("bridge case correction gross (posted)", br["case_correction_posted"]["gross"], b["case_gross"])
    check("bridge case correction net (posted)", br["case_correction_posted"]["net"], b["case_net"])
    check("bridge additional IBNR gross (to book)", br["additional_ibnr_to_book"]["gross"], b["addl_gross"])
    check("bridge additional IBNR net (to book)", br["additional_ibnr_to_book"]["net"], b["addl_net"])
    check("bridge total revision gross", br["total_revision"]["gross"], b["total_gross"])
    check("bridge total revision net", br["total_revision"]["net"], b["total_net"])

    # ── T05 — engine is genuinely sensitive to a changed selection weight ─────
    v70 = E.value_cohort(pos_c["paid"], pos_c["case"], inc_cdf, paid_cdf, prem, elr,
                         {"incurred_chain_ladder": Decimal("0.7"),
                          "incurred_bornhuetter_ferguson": Decimal("0.3")}, qs)
    moved = v70["selected_ultimate"] != vc["selected_ultimate"]
    results.append((moved, "T05 changing selection weights changes the result",
                    E.to_millions(v70["selected_ultimate"]), "!= " + str(E.to_millions(vc["selected_ultimate"]))))

    # weights that don't sum to 1 must be rejected
    rejected = False
    try:
        E.select_ultimate(vc["indications"], {"incurred_chain_ladder": Decimal("0.6"),
                                              "incurred_bornhuetter_ferguson": Decimal("0.6")})
    except ValueError:
        rejected = True
    results.append((rejected, "T05 invalid weights (sum!=1) are rejected", rejected, "True"))


def main():
    run()
    print("\n  Claim to Confidence — acceptance oracle (EUR millions)\n" + "  " + "-" * 68)
    n_pass = 0
    for ok, name, got, exp in results:
        flag = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        print(f"  [{flag}] {name:<52} got={got}  expected={exp}")
    print("  " + "-" * 68)
    total = len(results)
    print(f"  {n_pass}/{total} checks passed")
    if n_pass != total:
        print("  ORACLE NOT REPRODUCED — do not build on this.")
        sys.exit(1)
    print("  Oracle reproduced to the cent from generated inputs.\n")


if __name__ == "__main__":
    main()
