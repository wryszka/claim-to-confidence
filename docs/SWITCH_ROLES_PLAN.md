# Option B (staged) — live per-role authority via Databricks Switch Roles

**Status:** deferred by decision on 2026-09-10. Option A (below) is what ships today. This
document is the ready-to-run plan so Option B is a ~15-minute finish once the one prerequisite
(two account-level groups) exists.

## What ships today (Option A) — real, no dependencies

The app/agent identity's approval write is **denied by Unity Catalog itself**:
`PERMISSION_DENIED: User does not have MODIFY on Table …6_gov_decision`. The approvals table
`6_gov_decision` is writable only by the schema owner; the app service principal has `SELECT`
but no `MODIFY`. This is genuine data-tier authority (not a UI toggle) — one identity. Verified
live via `/api/agent/attempt?action=approve_reserve`.

## Why Option B needs a prerequisite I can't self-serve

Databricks **Switch Roles** (GA, docs.databricks.com/aws/en/security/auth/rbac/switch-roles) is
the ideal mechanism: a single user assumes a role, and Unity Catalog enforces that role's grants
for the session — no secrets, no extra accounts. **But roles are backed by account-level groups**,
and Unity Catalog only accepts account-level groups as principals (workspace-local groups fail with
`PRINCIPAL_DOES_NOT_EXIST`). Creating account groups needs **account-admin**, which this FEVM
workspace does not grant. So the two role groups must be created by an account admin (or via a FEVM
request) first.

## The prerequisite (account admin / FEVM, ~2 min)

```
databricks account groups create --display-name c2c-chief-actuary
databricks account groups create --display-name c2c-analyst
# add laurence.ryszka@databricks.com to BOTH groups (SCIM), and grant Assume on each
# (membership confers Assume per the Switch Roles docs)
```

## The finish (me, ~15 min once the groups exist)

1. **Differential Unity Catalog grants** (the whole point — chief can write approvals, analyst can't):
   ```sql
   -- both roles: read + run
   GRANT USE CATALOG ON CATALOG lr_dev_aws_us_catalog TO `c2c-chief-actuary`;
   GRANT USE SCHEMA, SELECT ON SCHEMA lr_dev_aws_us_catalog.claim_to_confidence TO `c2c-chief-actuary`;
   GRANT USE CATALOG ON CATALOG lr_dev_aws_us_catalog TO `c2c-analyst`;
   GRANT USE SCHEMA, SELECT ON SCHEMA lr_dev_aws_us_catalog.claim_to_confidence TO `c2c-analyst`;
   -- chief ONLY: write approvals
   GRANT MODIFY ON TABLE lr_dev_aws_us_catalog.claim_to_confidence.`6_gov_decision` TO `c2c-chief-actuary`;
   ```
   Plus warehouse `CAN_USE` for both groups.

2. **App on-behalf-of (OBO) wiring** — attempt the approval write as the *logged-in user's current
   role*, not the app SP:
   - `app.yaml`: declare user API scopes (e.g. `sql`) so the app receives the user token.
   - Backend: read `X-Forwarded-Access-Token`, build a `WorkspaceClient(host=…, token=that)` and run
     the `INSERT INTO 6_gov_decision …` through it. UC returns the real verdict for the assumed role.
   - Keep the app-SP path as the "agent identity" negative test (already real).

3. **Demo beat (Screen E / agent):** a live "Approve as my current workspace role" button.
   - Presenter switches role in the top-right (Chief Actuary ↔ Reserving Analyst).
   - Click Approve → **succeeds as chief, denied as analyst** — all enforced by Unity Catalog.
   - Audit shows `identity_metadata.run_by` = the real user, `run_as` = the assumed role.

4. **The one thing to validate live** (only a browser session can): confirm the app's OBO
   `X-Forwarded-Access-Token` carries the *switched* role. If it does → the in-app flip works. If it
   does not → fall back to demonstrating the flip in the SQL editor (switch role → run the INSERT →
   allow/deny), with the app narrating it. Either way the enforcement is real.

## Why this is an upgrade, not a gap

Option A already proves the platform enforces authority. Option B makes it a *visible, per-role live
flip* driven by a GA Databricks feature — a stronger beat, but not required for the demo to stand.
