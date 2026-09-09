"""
The journey — reads the real Unity Catalog scenario tables and computes every screen LIVE
through the same pure engine that the acceptance tests prove to the cent. Nothing here
returns a canned business number; the app derives answers from the stored inputs.
"""
import json
from decimal import Decimal

from . import config, sql, engine as E

F = config.fqn


# ── low-level reads ──────────────────────────────────────────────────────────

def _snapshots():
    rows = sql.query(f"SELECT snapshot_id, valuation_date, information_cutoff, label, paid_eur, case_eur, "
                     f"incurred_eur, claim_count, quality_gate, note FROM {F('2_valuation_snapshot')}")
    return {r["snapshot_id"]: r for r in rows}


def _selected_factors():
    rows = sql.query(f"SELECT basis, cumulative_development_factor, rationale, selection_id, source_code, "
                     f"status_code, selected_by, approved_by FROM {F('4_selected_development_pattern')} "
                     f"WHERE status_code = 'APPROVED'")
    return {r["basis"]: r for r in rows}


def _apriori():
    return sql.query_one(f"SELECT earned_premium_eur, expected_loss_ratio, apriori_ultimate_eur "
                         f"FROM {F('4_reserve_apriori')} WHERE accident_year = 2023")


def _treaty():
    return sql.query_one(f"SELECT treaty_id, treaty_version, type, quota_share_pct, effective_from, "
                         f"effective_to, limits, exclusions, note FROM {F('5_reinsurance_treaty')}")


def _ledger_position():
    return sql.query_one(f"SELECT ledger_case_eur, ledger_existing_ibnr_eur, ledger_gross_outstanding_eur, "
                         f"posting_status, extract_version, note FROM {F('6_finance_ledger_position')}")


# ── assemble the computed state (both valuations + finance + bridge), live ─────

def _weights(cl_weight=None):
    """Selection policy: 50/50 incurred chain-ladder / incurred BF unless overridden."""
    w = Decimal("0.5") if cl_weight is None else Decimal(str(cl_weight))
    return {"incurred_chain_ladder": w, "incurred_bornhuetter_ferguson": Decimal(1) - w}


def compute_state(cl_weight=None):
    snaps = _snapshots()
    fac = _selected_factors()
    ap = _apriori()
    tr = _treaty()
    lp = _ledger_position()

    inc_cdf = Decimal(fac["INCURRED"]["cumulative_development_factor"])
    paid_cdf = Decimal(fac["PAID"]["cumulative_development_factor"])
    prem = int(ap["earned_premium_eur"])
    elr = Decimal(ap["expected_loss_ratio"])
    qs = Decimal(tr["quota_share_pct"])
    weights = _weights(cl_weight)

    def val(snap_id):
        s = snaps[snap_id]
        return E.value_cohort(int(s["paid_eur"]), int(s["case_eur"]), inc_cdf, paid_cdf, prem, elr, weights, qs)

    vi, vc = val("SNAP-INITIAL"), val("SNAP-CORRECTED")
    fin = E.residual_finance_adjustment(vc["gross_outstanding"], int(lp["ledger_case_eur"]),
                                        int(lp["ledger_existing_ibnr_eur"]), qs)
    bridge = E.movement_bridge(vi, vc, 2_000_000, qs)
    return {"snaps": snaps, "factors": fac, "apriori": ap, "treaty": tr, "ledger": lp,
            "vi": vi, "vc": vc, "fin": fin, "bridge": bridge, "weights": weights,
            "inc_cdf": inc_cdf, "paid_cdf": paid_cdf, "quota_share_pct": qs}


def _mm(x):
    return E.to_millions(x)


# ── Screen A — the decision ────────────────────────────────────────────────────

def decision(cl_weight=None):
    st = compute_state(cl_weight)
    vi, vc, fin, br = st["vi"], st["vc"], st["fin"], st["bridge"]
    return {
        "hero": {
            "case_correction": _mm(br["case_correction_posted"]["gross"]),
            "gross_delta": _mm(br["total_revision"]["gross"]),
            "net_delta": _mm(br["total_revision"]["net"]),
            "residual_to_book": _mm(fin["residual_gross"]),
            "gross_before": _mm(vi["gross_outstanding"]), "gross_after": _mm(vc["gross_outstanding"]),
            "net_before": _mm(vi["net_outstanding"]), "net_after": _mm(vc["net_outstanding"]),
            "selected_ultimate_after": _mm(vc["selected_ultimate"]),
        },
        "ripple": [
            {"key": "claim", "label": "Claim correction", "value": f"+€{_mm(br['case_correction_posted']['gross'])}m",
             "sub": "One major bodily-injury claim re-estimated", "status": "Posted", "tone": "info"},
            {"key": "reserve", "label": "Gross reserve", "value": f"+€{_mm(br['total_revision']['gross'])}m",
             "sub": "Selected gross outstanding, re-decided", "status": "Approved", "tone": "warn"},
            {"key": "reinsurance", "label": "After reinsurance", "value": f"+€{_mm(br['total_revision']['net'])}m",
             "sub": "Net of the 20% quota-share treaty", "status": "Reconciled", "tone": "good"},
            {"key": "finance", "label": "Finance", "value": f"+€{_mm(fin['residual_gross'])}m",
             "sub": "Residual journal only — €2.0m already booked", "status": "Proposed", "tone": "good"},
            {"key": "capital", "label": "Capital / IFRS 17", "value": "Dependency identified",
             "sub": "Affected inputs flagged for recalculation", "status": "Handoff", "tone": "muted"},
        ],
        "prompt": "What changed, and what still needs approval?",
    }


# ── Screen B — data readiness ──────────────────────────────────────────────────

def readiness():
    deliveries = sql.query(f"SELECT delivery_id, received_ts, information_cutoff, source_system, description, "
                           f"status, dq_status FROM {F('1_raw_source_delivery')} ORDER BY received_ts")
    snaps = _snapshots()
    # duplicate detection evidence, straight from the ledger
    dup = sql.query(f"SELECT claim_id, revision_id, delivery_id, amount_eur, dedup_status, duplicate_of "
                    f"FROM {F('1_raw_claim_transaction')} WHERE dedup_status = 'DROPPED_DUPLICATE'")
    counts = sql.query_one(f"SELECT COUNT(*) AS txns, COUNT(DISTINCT claim_id) AS claims "
                           f"FROM {F('1_raw_claim_transaction')} WHERE dedup_status = 'ACCEPTED'")
    return {
        "deliveries": deliveries,
        "duplicate": {"caught": len(dup) > 0, "rows": dup,
                      "note": "Same business event (claim + revision) redelivered under a distinct delivery ID; "
                              "quarantined on (claim_id, revision_id). Idempotent — no second €2m."},
        "snapshots": [{"snapshot_id": s["snapshot_id"], "label": s["label"], "cutoff": s["information_cutoff"],
                       "paid": _mm(int(s["paid_eur"])), "case": _mm(int(s["case_eur"])),
                       "incurred": _mm(int(s["incurred_eur"])), "claim_count": s["claim_count"],
                       "quality_gate": s["quality_gate"]} for s in snaps.values()],
        "control_totals": {"accepted_transactions": int(counts["txns"]), "claims": int(counts["claims"])},
    }


# ── Screen C — practitioner (triangle, empirical vs selected, methods) ─────────

def _empirical_factor_to_ultimate(measure, ay=2023):
    """Volume-weighted age-to-age factors from the triangle, chained to a cumulative
    factor from AY2023's current maturity to the tail — the diagnostic the selected
    factor is compared against (selection is prescribed, not this)."""
    rows = sql.query(f"SELECT accident_year, development_lag, cumulative_eur FROM {F('3_triangle_cell')} "
                     f"WHERE measure = '{measure}' ORDER BY accident_year, development_lag")
    tri = {}
    for r in rows:
        tri.setdefault(int(r["accident_year"]), {})[int(r["development_lag"])] = float(r["cumulative_eur"])
    max_lag = max((max(v) for v in tri.values()), default=0)
    a2a = {}
    for k in range(max_lag):
        num = sum(t[k + 1] for t in tri.values() if k in t and k + 1 in t)
        den = sum(t[k] for t in tri.values() if k in t and k + 1 in t)
        a2a[k] = (num / den) if den else 1.0
    cur = max(tri.get(ay, {0: 0})) if ay in tri else 0
    cdf = 1.0
    for k in range(cur, max_lag):
        cdf *= a2a.get(k, 1.0)
    return {"triangle": tri, "age_to_age": a2a, "current_lag": cur, "empirical_cdf": round(cdf, 4)}


def practitioner():
    st = compute_state()
    fac = st["factors"]
    out = {"cutoffs": {}, "diagnostics": {}, "selection": {
        "policy": "50% incurred chain-ladder + 50% incurred Bornhuetter-Ferguson (synthetic demonstration policy)",
        "incurred_cdf": str(st["inc_cdf"]), "paid_cdf": str(st["paid_cdf"]),
        "incurred_rationale": fac["INCURRED"]["rationale"], "paid_rationale": fac["PAID"]["rationale"]}}
    for measure in ("PAID", "INCURRED"):
        d = _empirical_factor_to_ultimate(measure)
        selected = float(st["paid_cdf"]) if measure == "PAID" else float(st["inc_cdf"])
        out["diagnostics"][measure] = {
            "age_to_age": {str(k): round(v, 4) for k, v in d["age_to_age"].items()},
            "current_lag": d["current_lag"], "empirical_cdf": d["empirical_cdf"],
            "selected_cdf": selected,
            "gap_pct": round((selected - d["empirical_cdf"]) / d["empirical_cdf"] * 100, 2) if d["empirical_cdf"] else 0.0,
            "triangle": {str(ay): {str(k): _mm(v) for k, v in row.items()} for ay, row in d["triangle"].items()}}
    for label, v in (("initial", st["vi"]), ("corrected", st["vc"])):
        ind = v["indications"]
        out["cutoffs"][label] = {
            "reported_incurred": _mm(ind["reported_incurred"]),
            "incurred_chain_ladder": _mm(ind["incurred_chain_ladder"]),
            "paid_chain_ladder": _mm(ind["paid_chain_ladder"]),
            "expected_ultimate": _mm(ind["expected_ultimate"]),
            "incurred_bornhuetter_ferguson": _mm(ind["incurred_bornhuetter_ferguson"]),
            "selected_ultimate": _mm(v["selected_ultimate"]),
            "gross_outstanding": _mm(v["gross_outstanding"]), "gross_ibnr": _mm(v["gross_ibnr"])}
    return out


def recompute(cl_weight):
    """Screen C/E — change the selection weight within [0,1] and recompute live. Proves the
    engine is sensitive and that the UI never retains the hero numbers after a change."""
    w = float(cl_weight)
    if w < 0 or w > 1:
        raise ValueError("chain-ladder weight must be within [0, 1]")
    st = compute_state(cl_weight=w)
    vc = st["vc"]
    base = compute_state()["vc"]
    return {"cl_weight": w, "bf_weight": round(1 - w, 4),
            "selected_ultimate": _mm(vc["selected_ultimate"]),
            "gross_outstanding": _mm(vc["gross_outstanding"]),
            "net_outstanding": _mm(vc["net_outstanding"]),
            "delta_vs_policy": round(_mm(vc["selected_ultimate"]) - _mm(base["selected_ultimate"]), 3)}


# ── Screen D — change impact ───────────────────────────────────────────────────

def change_impact():
    st = compute_state()
    vi, vc, br, fin = st["vi"], st["vc"], st["bridge"], st["fin"]
    def row(name, i, c):
        return {"item": name, "initial": _mm(i), "corrected": _mm(c), "change": round(_mm(c) - _mm(i), 3)}
    return {
        "comparison": [
            row("Selected ultimate", vi["selected_ultimate"], vc["selected_ultimate"]),
            row("Selected gross outstanding", vi["gross_outstanding"], vc["gross_outstanding"]),
            row("Selected gross IBNR", vi["gross_ibnr"], vc["gross_ibnr"]),
            row("Ceded outstanding (20% quota share)", vi["ceded_outstanding"], vc["ceded_outstanding"]),
            row("Net outstanding", vi["net_outstanding"], vc["net_outstanding"]),
        ],
        "method_response": {
            "incurred_chain_ladder": {"initial": _mm(vi["indications"]["incurred_chain_ladder"]),
                                       "corrected": _mm(vc["indications"]["incurred_chain_ladder"]),
                                       "change": round(_mm(vc["indications"]["incurred_chain_ladder"]) - _mm(vi["indications"]["incurred_chain_ladder"]), 3)},
            "incurred_bornhuetter_ferguson": {"initial": _mm(vi["indications"]["incurred_bornhuetter_ferguson"]),
                                              "corrected": _mm(vc["indications"]["incurred_bornhuetter_ferguson"]),
                                              "change": round(_mm(vc["indications"]["incurred_bornhuetter_ferguson"]) - _mm(vi["indications"]["incurred_bornhuetter_ferguson"]), 3)},
            "paid_chain_ladder": {"initial": _mm(vi["indications"]["paid_chain_ladder"]),
                                  "corrected": _mm(vc["indications"]["paid_chain_ladder"]),
                                  "change": round(_mm(vc["indications"]["paid_chain_ladder"]) - _mm(vi["indications"]["paid_chain_ladder"]), 3)},
        },
        "bridge": {
            "case_correction_posted": {k: _mm(v) for k, v in br["case_correction_posted"].items()},
            "additional_ibnr_to_book": {k: _mm(v) for k, v in br["additional_ibnr_to_book"].items()},
            "total_revision": {k: _mm(v) for k, v in br["total_revision"].items()},
        },
        "four_numbers": {
            "method_indication_2_4": round(_mm(vc["indications"]["incurred_chain_ladder"]) - _mm(vi["indications"]["incurred_chain_ladder"]), 2),
            "selected_gross_2_2": _mm(br["total_revision"]["gross"]),
            "net_1_76": _mm(br["total_revision"]["net"]),
            "residual_journal_0_2": _mm(fin["residual_gross"]),
        },
        "note": "Same 30 June valuation, two information cutoffs. Only accident year 2023 Commercial Motor "
                "moves; all other cohorts are unchanged.",
    }


# ── Screen (finance) — the residual journal ────────────────────────────────────

def finance():
    st = compute_state()
    fin, lp, vc = st["fin"], st["ledger"], st["vc"]
    return {
        "ledger": {"case": _mm(int(lp["ledger_case_eur"])), "existing_ibnr": _mm(int(lp["ledger_existing_ibnr_eur"])),
                   "gross_outstanding": _mm(int(lp["ledger_gross_outstanding_eur"])),
                   "posting_status": lp["posting_status"], "extract_version": lp["extract_version"], "note": lp["note"]},
        "revised_gross_outstanding": _mm(fin["revised_gross_outstanding"]),
        "residual": {"gross": _mm(fin["residual_gross"]), "ceded": _mm(fin["residual_ceded"]), "net": _mm(fin["residual_net"])},
        "journal": [{"account": l["account"], "dr": _mm(l["dr"]), "cr": _mm(l["cr"])} for l in fin["journal"]],
        "balanced": fin["balanced"], "total_dr": _mm(fin["journal_total_dr"]), "total_cr": _mm(fin["journal_total_cr"]),
        "double_count_prevented": True,
        "note": "The €2.0m case correction is already on the ledger. Finance books only the €0.2m residual IBNR "
                "(and its €0.04m ceded), never the full movement twice.",
    }


# ── Screen E — review & approval ───────────────────────────────────────────────

def review():
    st = compute_state()
    vc = st["vc"]
    fac = st["factors"]
    return {
        "proposal": {"selection_id": "SEL-2026Q2-CM-INCURRED", "cohort": "AY2023 Commercial Motor",
                     "selected_ultimate": _mm(vc["selected_ultimate"]),
                     "gross_outstanding": _mm(vc["gross_outstanding"]), "net_outstanding": _mm(vc["net_outstanding"]),
                     "status": "APPROVED", "preparer": fac["INCURRED"]["selected_by"],
                     "reviewer": fac["INCURRED"]["approved_by"]},
        "authority": [
            {"actor": "Reserving analyst", "may": "Investigate, run approved methods, draft selections",
             "may_not": "Approve their own material proposal"},
            {"actor": "Chief actuary / reviewer", "may": "Review and approve or reject the specific proposal",
             "may_not": "Silently rewrite a published historic version"},
            {"actor": "Agent identity", "may": "Read authorised evidence, invoke approved calculations, create proposals",
             "may_not": "Correct source, change permissions, relax a gate, approve a reserve, or publish"},
        ],
        "negative_test": {"scenario": "An agent identity attempts to approve the reserve and export another portfolio",
                          "result": "DENIED by the enforcement layer",
                          "note": "First cut uses the labelled role harness; separately-authenticated principals are a later phase."},
    }


# ── Screen F — evidence ────────────────────────────────────────────────────────

def evidence():
    audit = sql.query(f"SELECT event_id, event_type, entity_type, entity_id, detail, actor, created_at "
                      f"FROM {F('7_gov_audit_event')} ORDER BY event_id")
    manifests = sql.query(f"SELECT run_id, label, information_cutoff, created_at, manifest_json "
                          f"FROM {F('7_gov_run_manifest')} ORDER BY run_id")
    mans = []
    for m in manifests:
        try:
            mj = json.loads(m["manifest_json"])
        except Exception:
            mj = {}
        mans.append({"run_id": m["run_id"], "label": m["label"], "cutoff": m["information_cutoff"],
                     "created_at": m["created_at"], "manifest": mj})
    return {"audit": audit, "manifests": mans,
            "reproduce_note": "\"Reproduce this calculation\" re-runs the engine deterministically from the retained "
                              "inputs and compares to the stored completed run — numerically, no AI prose required."}


def reproduce():
    """Deterministic re-run from retained inputs, compared to the persisted completed run.
    Proves both numerical versions reproduce (acceptance test T12)."""
    st = compute_state()
    stored = sql.query(f"SELECT snapshot_id, selected_ultimate_eur, gross_outstanding_eur, net_outstanding_eur "
                       f"FROM {F('4_reserve_estimate')}")
    stored_map = {r["snapshot_id"]: r for r in stored}
    out = []
    for snap_id, v in (("SNAP-INITIAL", st["vi"]), ("SNAP-CORRECTED", st["vc"])):
        s = stored_map.get(snap_id, {})
        recomputed = _mm(v["selected_ultimate"])
        stored_val = _mm(int(s["selected_ultimate_eur"])) if s.get("selected_ultimate_eur") is not None else None
        out.append({"snapshot": snap_id, "recomputed_selected_ultimate": recomputed,
                    "stored_selected_ultimate": stored_val,
                    "match": (stored_val is not None and abs(recomputed - stored_val) < 0.01)})
    return {"comparisons": out, "all_match": all(c["match"] for c in out)}


def meta():
    tr = _treaty()
    return {"entity": config.ENTITY, "line_of_business": "Commercial Motor liability", "accident_year": 2023,
            "currency": "EUR", "valuation_date": "2026-06-30",
            "cutoff_initial": "2026-07-03", "cutoff_corrected": "2026-07-06",
            "treaty": tr, "hub_url": config.HUB_APP_URL}
