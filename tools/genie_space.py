"""
Create the Genie space for the business-question entry point (spec §3A / §3H).

The space is scoped to the governed views the app publishes, so Genie answers over the SAME
numbers the journey computes and can distinguish approved / proposed / outstanding positions:

  * vw_genie_position  — the three-state business view (position_status column)
  * vw_group_headline  — headline KPIs
  * 6_gov_downstream_handoff, 6_gov_decision, 2_valuation_snapshot — supporting detail

Canonical creation path (see the internal `genie-rooms` skill / the project memory
`reference_genie_space_creation.md`): build the space with the genie-rooms GenieSpaceBuilder
and POST it via `databricks api post /api/2.0/genie/spaces --json @file`. The SDK create_space,
raw REST and CLI create-space paths fail on serialized_space encoding — do NOT use them.

This script assembles the space definition and writes the request payload; with --create it
posts via the CLI. It requires a working `databricks auth login` (blocked while the profile
token is invalid) and CAN_MANAGE on the warehouse. After creation, set GENIE_SPACE_ID in
app.yaml and redeploy; the Discover screen then shows the native Genie link.

    python3 tools/genie_space.py --print                    # emit the space definition
    python3 tools/genie_space.py --create --profile DEV     # create it (needs auth)
"""
import argparse
import json
import subprocess
import sys

CATALOG = "lr_dev_aws_us_catalog"
SCHEMA = "claim_to_confidence"
WAREHOUSE_ID = "a3b61648ea4809e3"

TITLE = "Bricksurance — Reserving position (Claim to Confidence)"
DESCRIPTION = ("Business Q&A over the governed AY2023 Commercial Motor reserving position. "
               "Distinguishes the previous approved position, the new information (now approved) "
               "and the outstanding downstream / finance work.")

TABLES = [f"{CATALOG}.{SCHEMA}.vw_genie_position",
          f"{CATALOG}.{SCHEMA}.vw_group_headline",
          f"{CATALOG}.{SCHEMA}.6_gov_downstream_handoff",
          f"{CATALOG}.{SCHEMA}.6_gov_decision",
          f"{CATALOG}.{SCHEMA}.2_valuation_snapshot"]

SAMPLE_QUESTIONS = [
    "What changed since the previous approved position, and what needs attention?",
    "What is approved now, what changed, and what still needs action?",
    "What is the net outstanding movement for AY2023 Commercial Motor?",
    "Which downstream domains are awaiting recalculation?",
    "Show the previous approved position versus the current approved position.",
]

INSTRUCTIONS = (
    "This space answers about ONE cohort: AY2023 Commercial Motor liability for Bricksurance SE "
    "(a fictional insurer; all data synthetic), in EUR millions, gross undiscounted. "
    "ALWAYS read vw_genie_position and respect its position_status column: PREVIOUS_APPROVED is the "
    "prior approved position, APPROVED_CURRENT is the current approved position after the €2.0m case "
    "correction, and OUTSTANDING_WORK is downstream / finance work that is NOT yet complete. "
    "NEVER present a proposal or an OUTSTANDING_WORK row as an approved result. When asked what changed, "
    "compare APPROVED_CURRENT to PREVIOUS_APPROVED and report the net movement. Do not invent statutory "
    "capital or IFRS 17 numbers — downstream results are 'awaiting recalculation'."
)


def space_definition():
    return {"display_name": TITLE, "description": DESCRIPTION, "warehouse_id": WAREHOUSE_ID,
            "table_identifiers": TABLES, "sample_questions": SAMPLE_QUESTIONS,
            "instructions": INSTRUCTIONS}


def create(profile):
    payload = space_definition()
    path = "docs/genie_space_request.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[genie] wrote request payload → {path}")
    cmd = ["databricks", "api", "post", "/api/2.0/genie/spaces", "--profile", profile, "--json", f"@{path}"]
    print("[genie] " + " ".join(cmd))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        print(f"[genie] FAILED to invoke the CLI: {e}")
        return 1
    if out.returncode != 0:
        print(f"[genie] CLI error (needs `databricks auth login` + CAN_MANAGE on the warehouse):\n{out.stderr[:600]}")
        print("[genie] Canonical fallback: use the internal genie-rooms GenieSpaceBuilder (see the docstring).")
        return 1
    try:
        resp = json.loads(out.stdout)
        sid = resp.get("space_id") or resp.get("id")
        print(f"[genie] created space {sid}. Set GENIE_SPACE_ID={sid} in app.yaml and redeploy.")
    except Exception:
        print("[genie] created; raw response:\n" + out.stdout[:600])
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    ap.add_argument("--profile", default="DEV")
    a = ap.parse_args()
    if a.show or not a.create:
        print(json.dumps(space_definition(), indent=2))
    if a.create:
        sys.exit(create(a.profile))
