"""
Apply the exact grants the app needs (spec §5 authority model). Idempotent; re-run after every
deploy (the schema is recreated, so schema/table grants must be re-applied).

The authority beat depends on getting this EXACT:
  * the app service principal may READ the whole scenario and MODIFY only the audit / AI-trace /
    scenario-state / proposal tables;
  * it is NOT granted MODIFY on 6_gov_decision or 7_gov_permission_probe — those denials are the
    real, data-tier enforcement shown in the demo.

    uv run --native-tls --with databricks-sdk tools/grants.py --profile DEV
"""
import argparse
import sys

CATALOG = "lr_dev_aws_us_catalog"
SCHEMA = "claim_to_confidence"
APP_SP = "623c0fcf-5487-47da-a929-563f7a7b6c35"
WAREHOUSE_ID = "a3b61648ea4809e3"
FM_ENDPOINT = "databricks-claude-sonnet-5"
MODIFY_TABLES = ["7_gov_audit_event", "7_gov_ai_trace", "0_cfg_scenario_state", "6_gov_proposal"]
# deliberately NOT granted MODIFY (the denial is the demo):
DENY_TABLES = ["6_gov_decision", "7_gov_permission_probe"]


def main(profile):
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient(profile=profile)
    fq = f"{CATALOG}.{SCHEMA}"

    def sql(stmt):
        r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WAREHOUSE_ID, wait_timeout="50s")
        st = r.status.state.value if r.status and r.status.state else "UNKNOWN"
        if st != "SUCCEEDED":
            msg = r.status.error.message if r.status and r.status.error else st
            raise RuntimeError(msg)

    grants = [
        f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{APP_SP}`",
        f"GRANT USE SCHEMA ON SCHEMA {fq} TO `{APP_SP}`",
        f"GRANT SELECT ON SCHEMA {fq} TO `{APP_SP}`",
    ] + [f"GRANT MODIFY ON TABLE {fq}.`{t}` TO `{APP_SP}`" for t in MODIFY_TABLES]
    for g in grants:
        sql(g)
        print(f"[grant] OK  {g}")
    print(f"[grant] (intentionally NOT granting MODIFY on {DENY_TABLES} — those denials are the authority beat)")

    # warehouse CAN_USE
    try:
        from databricks.sdk.service import sql as sqlsvc
        w.warehouses.update_permissions(warehouse_id=WAREHOUSE_ID, access_control_list=[
            sqlsvc.WarehouseAccessControlRequest(service_principal_name=APP_SP,
                                                 permission_level=sqlsvc.WarehousePermissionLevel.CAN_USE)])
        print(f"[grant] OK  warehouse {WAREHOUSE_ID} CAN_USE → app SP")
    except Exception as e:
        print(f"[grant] WARN warehouse ACL not set via SDK ({str(e)[:120]}); verify CAN_USE manually")

    # model endpoint CAN_QUERY
    try:
        from databricks.sdk.service import serving
        w.serving_endpoints.update_permissions(serving_endpoint_id=FM_ENDPOINT, access_control_list=[
            serving.ServingEndpointAccessControlRequest(service_principal_name=APP_SP,
                                                        permission_level=serving.ServingEndpointPermissionLevel.CAN_QUERY)])
        print(f"[grant] OK  serving endpoint {FM_ENDPOINT} CAN_QUERY → app SP")
    except Exception as e:
        print(f"[grant] WARN model endpoint ACL not set via SDK ({str(e)[:120]}); verify CAN_QUERY manually")

    print("[grant] done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="DEV")
    a = ap.parse_args()
    sys.exit(main(a.profile))
