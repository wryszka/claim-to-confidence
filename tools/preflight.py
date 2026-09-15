"""
Preflight (spec §6) — check every dependency before a run, from the app's own identity.

The real checks run inside the app (server/journey.preflight) so they exercise the app
service principal's access — the identity the demo actually uses. This CLI just calls the
deployed app's /api/preflight and prints each item with an actionable message, exiting
non-zero if the required set is not ready. A healthy web server alone is NOT a pass.

    python3 tools/preflight.py                     # against the deployed app
    python3 tools/preflight.py --url http://localhost:8000
"""
import argparse
import json
import sys
import urllib.request

DEFAULT_URL = "https://claim-to-confidence-7474656169654171.aws.databricksapps.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    a = ap.parse_args()
    endpoint = a.url.rstrip("/") + "/api/preflight"
    try:
        with urllib.request.urlopen(endpoint, timeout=90) as r:
            data = json.load(r)
    except Exception as e:
        print(f"[preflight] could not reach {endpoint}: {e}")
        print("[preflight] NOTE: a Databricks App requires an authenticated session; run this against a "
              "reachable app, or open /api/preflight in an authenticated browser tab.")
        return 2
    checks = data.get("checks", [])
    for c in checks:
        mark = "PASS" if c["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {c['check']:<20} {c['detail']}")
    print(f"\n  {data.get('passed')}/{data.get('total')} checks passed · ready={data.get('ready')}")
    print(f"  {data.get('note','')}")
    return 0 if data.get("ready") else 1


if __name__ == "__main__":
    sys.exit(main())
