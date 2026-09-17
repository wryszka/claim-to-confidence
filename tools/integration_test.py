"""
Integration tests (spec §8) — proven LOCALLY, without a workspace.

These exercise the REAL server code (journey / presenter / agent) against an in-memory table
store built from the same deterministic scenario the deploy writes to Unity Catalog. The store
is served through a small fake of server.sql, so the control logic is genuinely executed — not
re-implemented in the test. Workspace-only concerns (live Unity Catalog denial, the model
endpoint, Genie) are NOT claimed here; they are validated on the deployed instance and marked
'deployed' in ACCEPTANCE_TESTS.md.

Run:  python3 tools/integration_test.py
"""
import hashlib
import json
import re
import sys
from decimal import Decimal

sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "app")

import world_engine as W
import engine as E
import deploy_databricks as D

IV = "IV-2026-07-06-CORR-01"
DQ = [
    ("DQ-01", "ONESHIELD_CLAIMS", "Every claim transaction has a stable claim/revision id", "critical", "PASS"),
    ("DQ-02", "ONESHIELD_CLAIMS", "Ledger paid+case ties to the reported triangle diagonal", "critical", "PASS"),
    ("DQ-03", "ONESHIELD_CLAIMS", "No duplicate source-delivery of the same business event", "critical", "PASS"),
    ("DQ-04", "PREMIUM_SYSTEM", "Earned premium present for the a-priori basis", "critical", "PASS"),
    ("DQ-05", "ONESHIELD_CLAIMS", "Currency and segment mapping valid", "warning", "PASS"),
    ("DQ-06", "TREATY_REGISTER", "Reinsurance treaty version effective at both cutoffs", "critical", "PASS"),
]
COLUMN_ORDERS = {
    "6_gov_proposal": ["proposal_id", "scenario_id", "selection_id", "run_id", "cohort", "input_version",
                       "assumption_hash", "calc_version", "selected_ultimate_eur", "gross_outstanding_eur",
                       "gross_ibnr_eur", "ceded_outstanding_eur", "net_outstanding_eur", "proposal_hash",
                       "status", "preparer", "created_at"],
    "7_gov_permission_probe": ["probe_id", "attempted_by", "attempted_at", "target", "note"],
    "7_gov_ai_trace": ["trace_id", "correlation_id", "surface", "identity", "scenario_id", "run_id", "question",
                       "response", "grounding_refs", "endpoint", "model_config", "tool_calls", "error",
                       "policy_outcome", "created_at"],
    "7_gov_audit_event": ["event_id", "event_type", "entity_type", "entity_id", "detail", "actor", "created_at"],
}


def build_store():
    s = W.scenario(); meta = s["meta"]; ap = s["apriori"]
    weights = {k: Decimal(v) for k, v in meta["selection_weights"].items()}
    inc = Decimal(meta["selected_incurred_cdf"]); paid = Decimal(meta["selected_paid_cdf"])
    qs = Decimal(meta["quota_share_pct"]); elr = Decimal(meta["expected_loss_ratio"]); prem = ap["earned_premium"]
    vi = E.value_cohort(s["position_initial"]["paid"], s["position_initial"]["case"], inc, paid, prem, elr, weights, qs)
    vc = E.value_cohort(s["position_corrected"]["paid"], s["position_corrected"]["case"], inc, paid, prem, elr, weights, qs)
    lp = s["finance_ledger_position"]
    fin = E.residual_finance_adjustment(vc["gross_outstanding"], lp["ledger_case"], lp["ledger_existing_ibnr"], qs)
    bridge = E.movement_bridge(vi, vc, W.CORRECTION_EUR, qs)
    ah = E.assumption_fingerprint(inc, paid, prem, elr, weights, qs)
    phash = hashlib.sha256(f"PROP-2026Q2-CM-001|{IV}|{ah}|{int(vc['selected_ultimate'])}|"
                           f"{int(vc['gross_outstanding'])}".encode()).hexdigest()[:16]
    st = {}
    st["0_cfg_scenario_state"] = [{"scenario_id": "SC-BASE", "candidate_input_version": IV, "approved_input_version": IV,
                                   "defect_active": False, "defect_note": "", "calc_version": "1.0"}]
    st["2_valuation_snapshot"] = [
        {"snapshot_id": "SNAP-INITIAL", "valuation_date": meta["valuation_date"],
         "information_cutoff": meta["cutoff_initial"], "label": "Initial information (3 Jul)",
         "paid_eur": s["position_initial"]["paid"], "case_eur": s["position_initial"]["case"],
         "incurred_eur": s["position_initial"]["incurred"], "claim_count": len(s["claims"]), "quality_gate": "PASS",
         "note": "n"},
        {"snapshot_id": "SNAP-CORRECTED", "valuation_date": meta["valuation_date"],
         "information_cutoff": meta["cutoff_corrected"], "label": "Corrected information (6 Jul)",
         "paid_eur": s["position_corrected"]["paid"], "case_eur": s["position_corrected"]["case"],
         "incurred_eur": s["position_corrected"]["incurred"], "claim_count": len(s["claims"]), "quality_gate": "PASS",
         "note": "n"}]
    st["4_selected_development_pattern"] = [dict(p) for p in s["selected_patterns"]]
    st["4_reserve_apriori"] = [{"earned_premium_eur": ap["earned_premium"],
                                "expected_loss_ratio": ap["expected_loss_ratio"],
                                "apriori_ultimate_eur": ap["apriori_ultimate"], "accident_year": 2023,
                                "line_of_business_code": ap["line_of_business_code"]}]
    st["5_reinsurance_treaty"] = [dict(s["treaty"])]
    st["6_finance_ledger_position"] = [{"ledger_case_eur": lp["ledger_case"],
                                        "ledger_existing_ibnr_eur": lp["ledger_existing_ibnr"],
                                        "ledger_gross_outstanding_eur": lp["ledger_gross_outstanding"],
                                        "posting_status": lp["posting_status"], "extract_version": lp["extract_version"],
                                        "note": lp["note"]}]
    st["4_reserve_estimate"] = []
    for sid, v in (("SNAP-INITIAL", vi), ("SNAP-CORRECTED", vc)):
        st["4_reserve_estimate"].append({"snapshot_id": sid, "selected_ultimate_eur": int(v["selected_ultimate"]),
                                         "gross_outstanding_eur": int(v["gross_outstanding"]),
                                         "net_outstanding_eur": int(v["net_outstanding"]),
                                         "ceded_outstanding_eur": int(v["ceded_outstanding"]),
                                         "gross_ibnr_eur": int(v["gross_ibnr"])})
    st["3_triangle_cell"] = []
    for measure in ("PAID", "INCURRED"):
        for ay, row in s["triangle"][measure].items():
            for lag, cum in row.items():
                st["3_triangle_cell"].append({"measure": measure, "accident_year": ay, "development_lag": lag,
                                              "cumulative_eur": cum})
    st["1_raw_source_delivery"] = [dict(d) for d in s["deliveries"]]
    accepted_keys = {(t["claim_id"], t["revision_id"], t["delivery_id"]) for t in s["accepted_transactions"]}
    st["1_raw_claim_transaction"] = []
    for t in s["transactions"]:
        dedup = "ACCEPTED" if (t["claim_id"], t["revision_id"], t["delivery_id"]) in accepted_keys else "DROPPED_DUPLICATE"
        st["1_raw_claim_transaction"].append({"claim_id": t["claim_id"], "revision_id": t["revision_id"],
                                              "delivery_id": t["delivery_id"], "event_type": t["event_type"],
                                              "amount_eur": t["amount"], "dedup_status": dedup,
                                              "duplicate_of": t.get("duplicate_of")})
    st["1_raw_dq_check"] = [{"check_id": c[0], "source": c[1], "description": c[2], "severity": c[3], "status": c[4]}
                            for c in DQ]
    st["6_gov_proposal"] = [{"proposal_id": "PROP-2026Q2-CM-001", "scenario_id": "SC-BASE",
                             "selection_id": "SEL-2026Q2-CM-INCURRED", "run_id": "RUN-CORRECTED",
                             "cohort": "AY2023 Commercial Motor", "input_version": IV, "assumption_hash": ah,
                             "calc_version": "1.0", "selected_ultimate_eur": int(vc["selected_ultimate"]),
                             "gross_outstanding_eur": int(vc["gross_outstanding"]), "gross_ibnr_eur": int(vc["gross_ibnr"]),
                             "ceded_outstanding_eur": int(vc["ceded_outstanding"]),
                             "net_outstanding_eur": int(vc["net_outstanding"]), "proposal_hash": phash,
                             "status": "APPROVED", "preparer": "s.okonkwo@bricksurance.example", "created_at": "now"}]
    st["6_gov_decision"] = [{"decision_id": "DEC-2026Q2-CM", "scenario_id": "SC-BASE",
                             "proposal_id": "PROP-2026Q2-CM-001", "run_id": "RUN-CORRECTED",
                             "selection_id": "SEL-2026Q2-CM-INCURRED", "cohort": "AY2023 Commercial Motor",
                             "input_version": IV, "calc_version": "1.0", "assumption_hash": ah,
                             "selected_ultimate_eur": int(vc["selected_ultimate"]),
                             "gross_outstanding_eur": int(vc["gross_outstanding"]),
                             "ceded_outstanding_eur": int(vc["ceded_outstanding"]),
                             "net_outstanding_eur": int(vc["net_outstanding"]), "gross_ibnr_eur": int(vc["gross_ibnr"]),
                             "status": "APPROVED", "preparer": "s.okonkwo@bricksurance.example",
                             "reviewer": "chief.actuary@bricksurance.example", "decided_at": "now",
                             "proposal_hash": phash}]
    net_mv = int(vc["net_outstanding"] - vi["net_outstanding"]); gross_mv = int(vc["gross_outstanding"] - vi["gross_outstanding"])
    ceded_mv = int(vc["ceded_outstanding"] - vi["ceded_outstanding"])
    st["6_gov_downstream_handoff"] = [
        {"handoff_id": "HO-CAP-01", "handoff_version": 1, "domain": "CAPITAL", "target": "Solvency II SCR (reserve risk)",
         "affected_input": "Net technical-provision movement", "input_movement_eur": net_mv, "currency": "EUR",
         "valuation_date": meta["valuation_date"], "cohort_map": "m", "source_decision_id": "DEC-2026Q2-CM",
         "source_input_version": IV, "delivery_state": "DELIVERED", "result_state": "AWAITING_RECALCULATION",
         "idempotency_key": "DEC-2026Q2-CM|HO-CAP-01|" + IV, "note": "n"},
        {"handoff_id": "HO-IFRS-01", "handoff_version": 1, "domain": "IFRS17",
         "target": "Liability for incurred claims (PAA)", "affected_input": "Gross indemnity cash-flow movement",
         "input_movement_eur": gross_mv, "currency": "EUR", "valuation_date": meta["valuation_date"], "cohort_map": "m",
         "source_decision_id": "DEC-2026Q2-CM", "source_input_version": IV, "delivery_state": "DELIVERED",
         "result_state": "AWAITING_RECALCULATION", "idempotency_key": "DEC-2026Q2-CM|HO-IFRS-01|" + IV, "note": "n"},
        {"handoff_id": "HO-IFRS-02", "handoff_version": 1, "domain": "IFRS17", "target": "Reinsurance held (ceded)",
         "affected_input": "Ceded recoverable movement", "input_movement_eur": ceded_mv, "currency": "EUR",
         "valuation_date": meta["valuation_date"], "cohort_map": "m", "source_decision_id": "DEC-2026Q2-CM",
         "source_input_version": IV, "delivery_state": "DELIVERED", "result_state": "MAPPING_UNRESOLVED",
         "idempotency_key": "DEC-2026Q2-CM|HO-IFRS-02|" + IV, "note": "n"}]
    st["7_gov_run_manifest"] = []
    for rid, cut, v, f in (("RUN-INITIAL", meta["cutoff_initial"], vi, None),
                           ("RUN-CORRECTED", meta["cutoff_corrected"], vc, fin)):
        ivr = {"RUN-INITIAL": "IV-2026-07-03-INIT-01", "RUN-CORRECTED": IV}[rid]
        man = D.build_manifest(rid, meta, cut, v, f, bridge, ivr, ah)
        st["7_gov_run_manifest"].append({"run_id": rid, "label": rid.split("-")[1], "manifest_json": json.dumps(man, default=str)})
    st["7_gov_audit_event"] = []
    st["7_gov_ai_trace"] = []
    st["7_gov_permission_probe"] = []
    return st


class FakeSQL:
    """A minimal in-memory SQL served over a table store. Handles the SELECT/aggregate/INSERT/
    UPDATE/DELETE shapes the server actually issues. Writes to tables in `denied` raise a
    permission-shaped error, modelling the app SP lacking MODIFY."""

    def __init__(self, store, denied=("6_gov_decision", "7_gov_permission_probe"), probe_error=None):
        self.store = store
        self.denied = set(denied)
        self.probe_error = probe_error  # override to inject a non-permission error on the probe

    def esc(self, s):
        return (s or "").replace("'", "''") if s is not None else ""

    def _table(self, stmt):
        m = re.search(r"`([0-9A-Za-z_]+)`", stmt)
        return m.group(1) if m else None

    def _where(self, stmt):
        m = re.search(r"\bWHERE\b(.*?)(?:\bORDER BY\b|\bLIMIT\b|$)", stmt, re.S | re.I)
        if not m:
            return []
        preds = []
        for clause in re.split(r"\bAND\b", m.group(1), flags=re.I):
            mm = re.search(r"([\w.]+)\s*(=|LIKE)\s*'?([^']*?)'?\s*$", clause.strip(), re.I)
            if mm:
                preds.append((mm.group(1), mm.group(2).upper(), mm.group(3).strip()))
        return preds

    def _match(self, row, preds):
        for col, op, val in preds:
            rv = row.get(col)
            if op == "=":
                if str(rv) != val:
                    return False
            elif op == "LIKE":
                if not str(rv).startswith(val.rstrip("%")):
                    return False
        return True

    def query(self, stmt):
        s = stmt.strip()
        verb = s.split()[0].upper()
        table = self._table(s)
        if verb == "SELECT":
            if table is None:
                return [{"ok": 1}]
            rows = [r for r in self.store.get(table, []) if self._match(r, self._where(s))]
            if re.search(r"\bCOUNT\s*\(", s, re.I) or re.search(r"\bSUM\s*\(", s, re.I):
                out = {}
                for expr, alias in re.findall(r"(COUNT\s*\(\s*(?:DISTINCT\s+)?[\w*]+\s*\)|SUM\s*\(\s*\w+\s*\))\s+AS\s+(\w+)", s, re.I):
                    e = expr.upper().replace(" ", "")
                    if e.startswith("COUNT(DISTINCT"):
                        col = re.search(r"DISTINCT\s+(\w+)", expr, re.I).group(1)
                        out[alias] = len({r.get(col) for r in rows})
                    elif e.startswith("COUNT("):
                        out[alias] = len(rows)
                    elif e.startswith("SUM("):
                        col = re.search(r"SUM\s*\(\s*(\w+)\s*\)", expr, re.I).group(1)
                        out[alias] = sum(int(r.get(col) or 0) for r in rows)
                return [out]
            return [dict(r) for r in rows]
        if verb == "INSERT":
            if table in self.denied:
                if table == "7_gov_permission_probe" and self.probe_error:
                    raise RuntimeError(self.probe_error)
                raise RuntimeError(f"PERMISSION_DENIED: User does not have MODIFY on Table '{table}'")
            self._insert(s, table)
            return []
        if verb == "UPDATE":
            if table in self.denied:
                raise RuntimeError(f"PERMISSION_DENIED: User does not have MODIFY on Table '{table}'")
            self._update(s, table)
            return []
        if verb == "DELETE":
            if table in self.denied:
                raise RuntimeError(f"PERMISSION_DENIED: User does not have MODIFY on Table '{table}'")
            preds = self._where(s)
            self.store[table] = [r for r in self.store.get(table, []) if not self._match(r, preds)]
            return []
        return []

    def query_one(self, stmt):
        rows = self.query(stmt)
        return rows[0] if rows else None

    def _split_top(self, blob):
        parts, cur, q = [], "", False
        for ch in blob:
            if ch == "'":
                q = not q; cur += ch
            elif ch == "," and not q:
                parts.append(cur.strip()); cur = ""
            else:
                cur += ch
        if cur.strip():
            parts.append(cur.strip())
        return parts

    def _split_values(self, blob):
        return [self._coerce(v) for v in self._split_top(blob)]

    def _coerce(self, v):
        v = v.strip()
        if v.startswith("'") and v.endswith("'"):
            return v[1:-1].replace("''", "'")
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        try:
            return int(v)
        except ValueError:
            return v

    def _insert(self, s, table):
        cols_m = re.search(r"INSERT INTO\s+[^\(]*\(([^)]*)\)\s*VALUES", s, re.I)
        vals_m = re.search(r"VALUES\s*\((.*)\)\s*$", s, re.S | re.I)
        vals = self._split_values(vals_m.group(1))
        if cols_m:
            cols = [c.strip() for c in cols_m.group(1).split(",")]
        else:
            cols = COLUMN_ORDERS[table]
        self.store.setdefault(table, []).append(dict(zip(cols, vals)))

    def _update(self, s, table):
        set_m = re.search(r"\bSET\b(.*?)\bWHERE\b", s, re.S | re.I)
        preds = self._where(s)
        assigns = []
        for a in self._split_top(set_m.group(1)):
            mm = re.match(r"\s*(\w+)\s*=\s*(.*)", a.strip(), re.S)
            assigns.append((mm.group(1), self._coerce(mm.group(2))))
        for r in self.store.get(table, []):
            if self._match(r, preds):
                for k, v in assigns:
                    r[k] = v


# ── test harness ───────────────────────────────────────────────────────────────
PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"   {extra}" if extra and not ok else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def patch(fake):
    import server.sql as sql
    sql.query = fake.query
    sql.query_one = fake.query_one


def main():
    import os
    os.environ["PRESENTER_TOKEN"] = "present"  # presenter now fails closed unless a token is set
    import server.config as config
    config.get_workspace_client = lambda: (_ for _ in ()).throw(RuntimeError("no client in test"))
    import server.journey as journey
    import server.presenter as presenter
    import server.agent as agent
    agent._identity = lambda: "app-service-principal"

    print("Integration tests (local, real server code over an in-memory store)")

    # ── reproduction from retained artifacts, whole-EUR, all outputs ──
    patch(FakeSQL(build_store()))
    rep = journey.reproduce()
    check("IT-REPRO survives changed current defaults (reads retained manifest)", rep["reproducible"] is True)
    comps = [c for r in rep["runs"] for c in r["comparisons"]]
    fields = {c["field"] for c in comps}
    check("IT-REPRO compares all material outputs at whole EUR",
          {"selected_ultimate", "gross_outstanding", "gross_ibnr", "ceded_outstanding", "net_outstanding",
           "finance.residual_gross"} <= fields)
    check("IT-REPRO every retained field matches to the EUR", all(c["match"] for c in comps))

    # missing manifest fails visibly
    fk = FakeSQL(build_store()); fk.store["7_gov_run_manifest"] = []; patch(fk)
    check("IT-REPRO missing artifact fails visibly", journey.reproduce()["reproducible"] is False)

    # unsupported calc version fails visibly
    fk = FakeSQL(build_store())
    m0 = json.loads(fk.store["7_gov_run_manifest"][1]["manifest_json"]); m0["calc_version"] = "9.9"
    fk.store["7_gov_run_manifest"][1]["manifest_json"] = json.dumps(m0); patch(fk)
    rr = journey.reproduce()
    check("IT-REPRO unsupported calc version fails visibly",
          any(r["status"] == "FAILED" for r in rr["runs"]) and rr["reproducible"] is False)

    # ── approved decision resolved by explicit ids; reports resolve the SAME artifact ──
    patch(FakeSQL(build_store()))
    dec = journey.approved_decision()
    check("IT-APPROVE approved decision resolved by explicit ids", dec and dec["decision_id"] == "DEC-2026Q2-CM")
    rv = journey.review()
    cr = journey.committee_report()
    ln = journey.lineage()
    same = (rv["approval"]["decision_id"] == cr["decision_id"] == ln["chain"][1]["ref"] == "DEC-2026Q2-CM")
    check("IT-APPROVE review/report/lineage resolve the same approved artifact", same)
    check("IT-APPROVE committee memo generated from retained artifacts", cr["available"] is True)

    # ── missing approval never displays APPROVED (no fabrication) ──
    fk = FakeSQL(build_store()); fk.store["6_gov_decision"] = []; patch(fk)
    check("IT-NOAPPROVE review shows NOT_APPROVED when no decision", journey.review()["approval_status"] == "NOT_APPROVED")
    check("IT-NOAPPROVE committee memo unavailable when no decision", journey.committee_report().get("available") is False)
    check("IT-NOAPPROVE lineage does not fabricate an approval", journey.lineage()["chain"][1]["value"] == "NO APPROVED DECISION")

    # ── readiness gate ties to candidate version; defect blocks; correction releases ──
    fk = FakeSQL(build_store()); patch(fk)
    check("IT-GATE released at rest", journey.readiness()["gate"]["status"] == "RELEASED")
    presenter.introduce_defect("SC-BASE", token="present")
    g = journey.readiness()["gate"]
    check("IT-GATE a critical defect BLOCKS release", g["status"] == "BLOCKED" and g["defect_active"] is True)
    check("IT-GATE create-proposal refused while blocked",
          presenter.create_proposal("SC-BASE", token="present").get("refused") == "GATE_BLOCKED")
    presenter.correct_defect("SC-BASE", token="present")
    check("IT-GATE correction RELEASES a new candidate version", journey.readiness()["gate"]["status"] == "RELEASED")

    # ── preparer cannot self-approve; a distinct reviewer clears SoD; stale rejected ──
    fk = FakeSQL(build_store()); patch(fk)
    prop = presenter.create_proposal("SC-BASE", token="present")
    pid = prop["proposal_id"]
    self_ap = presenter.approve("SC-BASE", pid, reviewer="s.okonkwo@bricksurance.example", token="present")
    check("IT-SOD preparer cannot self-approve", self_ap.get("refused") == "SELF_APPROVAL")
    ok_ap = presenter.approve("SC-BASE", pid, reviewer="chief.actuary@bricksurance.example", token="present")
    check("IT-SOD distinct reviewer passes SoD then hits real UC denial (no fake approval)",
          ok_ap.get("refused") == "REQUIRES_REVIEWER_PRINCIPAL" and ok_ap.get("pre_conditions") == "ALL PASSED")
    # now move the version → the proposal becomes stale → approval rejected as stale
    presenter.create_next_version("SC-BASE", token="present")
    stale_ap = presenter.approve("SC-BASE", pid, reviewer="chief.actuary@bricksurance.example", token="present")
    check("IT-STALE stale proposal cannot be approved", stale_ap.get("refused") == "STALE_PROPOSAL")

    # ── agent cannot approve; infra error ≠ permission denial ──
    fk = FakeSQL(build_store()); patch(fk)  # decision + probe are denied (permission-shaped)
    r = agent.attempt_privileged_action("approve_reserve")
    check("IT-AGENT approve denied and classified CONFIRMED_DENIAL", r["result"] == "CONFIRMED_DENIAL" and r["enforced_by"] == "unity_catalog")
    check("IT-AGENT denial targets the isolated probe, never the approvals table", "permission_probe" in r["target"])
    fk2 = FakeSQL(build_store(), probe_error="Connection timed out contacting the warehouse"); patch(fk2)
    r2 = agent.attempt_privileged_action("approve_reserve")
    check("IT-AGENT infrastructure error is INCONCLUSIVE, not a permission denial", r2["result"] == "INCONCLUSIVE")
    fk3 = FakeSQL(build_store(), denied=())  # probe writable → control failure
    patch(fk3)
    r3 = agent.attempt_privileged_action("approve_reserve")
    check("IT-AGENT unexpected write success is a CONTROL_FAILURE (isolated, no business approval)",
          r3["result"] == "CONTROL_FAILURE")

    # ── downstream: idempotent, versioned; journal generated not posted ──
    patch(FakeSQL(build_store()))
    dn = journey.downstream()
    keys = [h["idempotency_key"] for h in dn["handoffs"]]
    check("IT-DOWNSTREAM versioned + unique idempotency keys", len(keys) == len(set(keys)) == 3)
    check("IT-DOWNSTREAM inputs delivered, result awaiting recalculation (not accepted, not fabricated)",
          all(h["delivery_state"] == "DELIVERED" for h in dn["handoffs"]) and
          any(h["result_state"] == "AWAITING_RECALCULATION" for h in dn["handoffs"]))
    fin = journey.finance()
    check("IT-FINANCE journal generated, not posted", fin["journal_state"] == "GENERATED_NOT_POSTED")
    check("IT-FINANCE residual is €0.2m, not the full €2.2m movement", fin["residual"]["gross"] == 0.2)

    # ── reset preserves evidence ──
    fk = FakeSQL(build_store()); patch(fk)
    presenter.create_proposal("SC-BASE", token="present")
    audit_before = len(fk.store["7_gov_audit_event"])
    man_before = len(fk.store["7_gov_run_manifest"])
    res = presenter.rehearsal_reset("SC-BASE", token="present")
    check("IT-RESET rehearsal proposals cleared", not any(p["proposal_id"].startswith("PROP-REH-") for p in fk.store["6_gov_proposal"]))
    check("IT-RESET seeded proposal + decision preserved",
          any(p["proposal_id"] == "PROP-2026Q2-CM-001" for p in fk.store["6_gov_proposal"]) and len(fk.store["6_gov_decision"]) == 1)
    check("IT-RESET retained run manifests preserved", len(fk.store["7_gov_run_manifest"]) == man_before)
    check("IT-RESET audit log only grows (evidence preserved)", len(fk.store["7_gov_audit_event"]) >= audit_before)

    # ── presenter mutations require the token (off the audience path) ──
    patch(FakeSQL(build_store()))
    check("IT-AUTH presenter mutation refused without token", presenter.introduce_defect("SC-BASE", token=None).get("ok") is False)

    print(f"\n  {PASS}/{PASS+FAIL} integration checks passed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
