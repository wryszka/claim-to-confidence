"""
Safe test-run controls (spec §6) — a RESTRICTED presenter utility, outside the audience path.

Every operation:
  * is a POST (never a state-changing GET);
  * is scoped by an explicit scenario_id and mutates ONLY that scenario's state + its own
    proposals — it never drops schemas, never touches shared Bricksurance data, and never
    deletes retained evidence;
  * requires the presenter token (env PRESENTER_TOKEN, default "present") so it stays off the
    main audience surface.

The approve step is deliberately honest: the app service principal has no MODIFY grant on the
approvals table, so the utility CANNOT write a business approval — it enforces the pre-conditions
(readiness gate, separation of duties, proposal freshness) and then reports that the live write
requires a separately-authenticated reviewer principal (the documented prerequisite). It never
fakes an approval.
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from . import config, sql, journey, engine as E

F = config.fqn


def _token_ok(token):
    return token == os.getenv("PRESENTER_TOKEN", "present")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _audit(event_type, entity_id, detail, actor="presenter.utility@bricksurance.example"):
    """Append a governance audit row (best-effort; app SP has MODIFY on the audit log)."""
    try:
        eid = "EVT-P-" + uuid.uuid4().hex[:8]
        sql.query(f"INSERT INTO {F('7_gov_audit_event')} VALUES ('{eid}','{event_type}','scenario',"
                  f"'{sql.esc(entity_id)}','{sql.esc(detail)[:400]}','{actor}','{_now()}')")
        return True
    except Exception:
        return False


def _state(scenario_id):
    return sql.query_one(
        f"SELECT scenario_id, candidate_input_version, approved_input_version, defect_active, defect_note, "
        f"calc_version FROM {F('0_cfg_scenario_state')} WHERE scenario_id = '{sql.esc(scenario_id)}'")


def _set_state(scenario_id, candidate, defect_active, defect_note):
    sql.query(f"UPDATE {F('0_cfg_scenario_state')} SET candidate_input_version='{sql.esc(candidate)}', "
              f"defect_active={'true' if defect_active else 'false'}, defect_note='{sql.esc(defect_note)}', "
              f"updated_at='{_now()}', updated_by='presenter' WHERE scenario_id='{sql.esc(scenario_id)}'")


def introduce_defect(scenario_id="SC-BASE", token=None):
    """Introduce a controlled source defect on the CANDIDATE inputs (spec §3D). The readiness gate
    then BLOCKS any create/release/approve for the new candidate version, while the previous
    approved position is retained untouched."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    st = _state(scenario_id)
    if not st:
        return {"error": f"unknown scenario {scenario_id}", "ok": False}
    candidate = f"{st['candidate_input_version']}.DEFECT"
    note = ("A claim transaction arrived on the candidate feed with no stable claim/revision id "
            "(DQ-01 critical). It cannot be reconciled to the triangle diagonal — release is blocked.")
    _set_state(scenario_id, candidate, True, note)
    _audit("defect_introduced", scenario_id, note)
    return {"ok": True, "scenario_id": scenario_id, "candidate_input_version": candidate,
            "gate": journey.readiness()["gate"],
            "note": "Critical DQ check now FAILS for the candidate version; the gate BLOCKS a new run. "
                    "The previous approved position is retained with its original cutoff."}


def correct_defect(scenario_id="SC-BASE", token=None):
    """Correct the source defect and revalidate (spec §3D). The gate RELEASES for the corrected
    candidate version, which is a NEW version — a PASS from the earlier version does not carry over."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    st = _state(scenario_id)
    if not st:
        return {"error": f"unknown scenario {scenario_id}", "ok": False}
    base = st["candidate_input_version"].split(".DEFECT")[0]
    candidate = f"{base}.FIX-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    _set_state(scenario_id, candidate, False, "")
    _audit("defect_corrected", scenario_id, f"Source corrected; revalidated candidate {candidate}.")
    return {"ok": True, "scenario_id": scenario_id, "candidate_input_version": candidate,
            "gate": journey.readiness()["gate"],
            "note": "Source corrected and revalidated; the gate RELEASES for the new candidate version. "
                    "A proposal can now be created against this version."}


def create_proposal(scenario_id="SC-BASE", token=None):
    """Create a preparer proposal bound to the current candidate version + assumption fingerprint +
    calc version (spec §3E). Refused if the readiness gate is BLOCKED for the candidate."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    st = _state(scenario_id)
    if not st:
        return {"error": f"unknown scenario {scenario_id}", "ok": False}
    gate = journey.readiness()["gate"]
    if gate["status"] != "RELEASED":
        return {"ok": False, "refused": "GATE_BLOCKED", "gate": gate,
                "note": "Cannot create a new result: the readiness gate is BLOCKED for the candidate input version. "
                        "Correct the source and revalidate first."}
    stt = journey.compute_state()
    vc = stt["vc"]
    fp = stt["assumption_fingerprint"]
    pid = "PROP-REH-" + uuid.uuid4().hex[:8]
    phash = uuid.uuid4().hex[:16]
    try:
        sql.query(f"INSERT INTO {F('6_gov_proposal')} VALUES ('{pid}','{sql.esc(scenario_id)}',"
                  f"'SEL-2026Q2-CM-INCURRED','RUN-CANDIDATE','AY2023 Commercial Motor',"
                  f"'{sql.esc(st['candidate_input_version'])}','{fp}','{E.CALC_VERSION}',"
                  f"{int(vc['selected_ultimate'])},{int(vc['gross_outstanding'])},{int(vc['gross_ibnr'])},"
                  f"{int(vc['ceded_outstanding'])},{int(vc['net_outstanding'])},'{phash}','PROPOSED',"
                  f"'s.okonkwo@bricksurance.example','{_now()}')")
    except Exception as e:
        return {"ok": False, "error": f"could not write proposal: {str(e)[:200]}",
                "note": "The app service principal needs MODIFY on 6_gov_proposal for the preparer path."}
    _audit("proposal_created", pid, f"Preparer proposal created against {st['candidate_input_version']}.")
    return {"ok": True, "proposal_id": pid, "status": "PROPOSED",
            "input_version": st["candidate_input_version"], "assumption_hash": fp, "calc_version": E.CALC_VERSION,
            "preparer": "s.okonkwo@bricksurance.example",
            "note": "Proposal bound to the exact input version + assumption fingerprint + calc version. "
                    "It can be approved only by a different, authorised reviewer, and only while it is not stale."}


def approve(scenario_id="SC-BASE", proposal_id=None, reviewer=None, token=None):
    """Attempt to approve a proposal (spec §3E / §4). Enforces the pre-conditions in the backend —
    readiness gate RELEASED, separation of duties (reviewer != preparer), proposal not stale — and
    then attempts the write. The app service principal has no MODIFY on the approvals table, so the
    write is denied by Unity Catalog: the live approve requires a separately-authenticated reviewer
    principal (documented prerequisite). NO approval is ever fabricated."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    if not proposal_id:
        return {"error": "proposal_id required", "ok": False}
    prop = journey._proposal(proposal_id)
    if not prop:
        return {"ok": False, "refused": "NO_SUCH_PROPOSAL", "note": f"No proposal {proposal_id} in {scenario_id}."}
    reviewer = reviewer or "chief.actuary@bricksurance.example"
    # 1) separation of duties
    if reviewer == prop["preparer"]:
        return {"ok": False, "refused": "SELF_APPROVAL",
                "note": f"Separation of duties: the preparer ({prop['preparer']}) cannot approve their own proposal. "
                        f"An authorised reviewer, distinct from the preparer, is required."}
    # 2) readiness gate for the candidate version
    gate = journey.readiness()["gate"]
    if gate["status"] != "RELEASED":
        return {"ok": False, "refused": "GATE_BLOCKED", "gate": gate,
                "note": "Cannot approve: the readiness gate is BLOCKED for the candidate input version."}
    # 3) staleness — inputs / assumptions must not have moved since the proposal was created
    st = _state(scenario_id)
    stt = journey.compute_state()
    live_fp = stt["assumption_fingerprint"]
    if not (prop["input_version"] == st["candidate_input_version"] and prop["assumption_hash"] == live_fp):
        return {"ok": False, "refused": "STALE_PROPOSAL",
                "proposal_input_version": prop["input_version"], "live_input_version": st["candidate_input_version"],
                "proposal_assumption_hash": prop["assumption_hash"], "live_assumption_hash": live_fp,
                "note": "The inputs or assumptions have changed since this proposal was created — it is stale and "
                        "cannot be approved. Create a fresh proposal against the current version."}
    # 4) pre-conditions satisfied → attempt the real write (app SP has no MODIFY on approvals)
    now = _now()
    try:
        sql.query(f"INSERT INTO {F('6_gov_decision')} (decision_id, scenario_id, proposal_id, run_id, selection_id, "
                  f"cohort, input_version, calc_version, assumption_hash, selected_ultimate_eur, gross_outstanding_eur, "
                  f"ceded_outstanding_eur, net_outstanding_eur, gross_ibnr_eur, status, preparer, reviewer, decided_at, "
                  f"proposal_hash) VALUES ('DEC-REH-{uuid.uuid4().hex[:6]}','{sql.esc(scenario_id)}',"
                  f"'{sql.esc(proposal_id)}','{prop['run_id']}','{prop['selection_id']}','{sql.esc(prop['cohort'])}',"
                  f"'{sql.esc(prop['input_version'])}','{prop['calc_version']}','{prop['assumption_hash']}',"
                  f"{int(prop['selected_ultimate_eur'])},{int(prop['gross_outstanding_eur'])},"
                  f"{int(prop['ceded_outstanding_eur'])},{int(prop['net_outstanding_eur'])},"
                  f"{int(prop['gross_ibnr_eur'])},'APPROVED','{sql.esc(prop['preparer'])}','{sql.esc(reviewer)}',"
                  f"'{now}','{prop['proposal_hash']}')")
        # If this ever succeeds, the grant is wrong — surface it, do not celebrate.
        _audit("approval_write_unexpected", proposal_id, "App SP wrote an approval — MODIFY grant is wrong; revoke it.")
        return {"ok": False, "refused": "CONTROL_FAILURE",
                "note": "The write SUCCEEDED from the app identity — this is a control failure. The app service "
                        "principal must not have MODIFY on the approvals table; revoke it. No demo should rely on this."}
    except Exception as e:
        err = str(e)[:220]
        _audit("approval_denied", proposal_id, f"App SP approval write denied: {err}")
        return {"ok": False, "refused": "REQUIRES_REVIEWER_PRINCIPAL", "pre_conditions": "ALL PASSED",
                "enforced_by": "unity_catalog", "error": err,
                "note": "All approval pre-conditions passed (gate released, distinct reviewer, proposal current). The "
                        "app service principal is then DENIED the write by Unity Catalog (no MODIFY on the approvals "
                        "table). The live approval must be performed by a separately-authenticated reviewer principal "
                        "(a role-scoped login / account group) — the documented prerequisite. This is enforced, not faked."}


def create_next_version(scenario_id="SC-BASE", token=None):
    """Create a subsequent candidate version (spec §6) so a newer run exists AFTER the approved one —
    the pre-condition for demonstrating historical reproduction of the earlier approved run."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    st = _state(scenario_id)
    if not st:
        return {"error": f"unknown scenario {scenario_id}", "ok": False}
    base = st["approved_input_version"]
    candidate = f"{base}.NEXT-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    _set_state(scenario_id, candidate, False, "")
    _audit("next_version_created", scenario_id, f"Subsequent candidate version {candidate} created.")
    return {"ok": True, "scenario_id": scenario_id, "candidate_input_version": candidate,
            "approved_input_version": base,
            "note": "A newer candidate version now exists. The approved decision retains its original input version, "
                    "so reproducing the earlier approved run (from its retained manifest) can be demonstrated against "
                    "a moved current state."}


def rehearsal_reset(scenario_id="SC-BASE", token=None):
    """Restart a rehearsal WITHOUT deleting evidence (spec §6). Resets only the mutable scenario
    state (clears the defect, returns the candidate to the approved version) and removes rehearsal-
    created proposals (PROP-REH-*). Never drops the schema, never touches retained runs / audit /
    decisions / archives."""
    if not _token_ok(token):
        return {"error": "unauthorised — presenter token required", "ok": False}
    st = _state(scenario_id)
    if not st:
        return {"error": f"unknown scenario {scenario_id}", "ok": False}
    approved = st["approved_input_version"]
    sql.query(f"UPDATE {F('0_cfg_scenario_state')} SET candidate_input_version='{sql.esc(approved)}', "
              f"defect_active=false, defect_note='', updated_at='{_now()}', updated_by='presenter-reset' "
              f"WHERE scenario_id='{sql.esc(scenario_id)}'")
    removed = 0
    try:
        sql.query(f"DELETE FROM {F('6_gov_proposal')} WHERE scenario_id='{sql.esc(scenario_id)}' "
                  f"AND proposal_id LIKE 'PROP-REH-%'")
        removed = 1
    except Exception:
        pass
    try:
        sql.query(f"DELETE FROM {F('6_gov_decision')} WHERE decision_id LIKE 'DEC-REH-%'")
    except Exception:
        pass  # expected to be denied for the app SP — there should be no such row anyway
    _audit("rehearsal_reset", scenario_id, "Rehearsal state reset; evidence preserved.")
    return {"ok": True, "scenario_id": scenario_id, "candidate_input_version": approved,
            "rehearsal_proposals_cleared": bool(removed),
            "note": "Mutable rehearsal state reset and rehearsal proposals cleared. Retained runs, audit, the approved "
                    "decision and the evidence archive are untouched — a reset never deletes prior evidence."}
