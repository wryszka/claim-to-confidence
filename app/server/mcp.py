"""
MCP endpoint (JSON-RPC 2.0) for the claim-to-confidence node, so the Group Control Tower
can discover and call this workbench like any other estate node. Two tools:

  * read_estimates      → headline KPIs (the tower surfaces the numeric fields)
  * read_flagged_items  → the attention queue (the tower maps items to attention rows)

Read-only; every number is computed live through the same engine the acceptance tests prove.
"""
import json
import logging

from fastapi import APIRouter, Request

from . import journey

logger = logging.getLogger(__name__)
router = APIRouter()

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "claim-to-confidence-workbench", "version": "1.0.0"}

TOOLS = [
    {"name": "read_estimates",
     "description": "Headline KPIs for the AY2023 Commercial Motor connected journey — gross/net "
                    "outstanding, the movement from the €2m correction, and the residual still to book.",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "read_flagged_items",
     "description": "The 'needs attention' queue — the reserve revision awaiting nothing further, the "
                    "quarantined duplicate delivery, the residual finance journal, and the capital hand-off.",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
]


def _ok(i, result):
    return {"jsonrpc": "2.0", "id": i, "result": result}


def _err(i, code, msg):
    return {"jsonrpc": "2.0", "id": i, "error": {"code": code, "message": msg}}


def _tool_result(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}],
            "structuredContent": payload,
            "isError": bool(isinstance(payload, dict) and payload.get("ok") is False)}


def _read_estimates():
    d = journey.decision()
    ci = journey.change_impact()
    h = d["hero"]
    return {"kpis": {
        "gross_outstanding_m": h["gross_after"], "net_outstanding_m": h["net_after"],
        "gross_movement_m": h["gross_delta"], "net_movement_m": h["net_delta"],
        "residual_to_book_m": h["residual_to_book"], "selected_ultimate_m": h["selected_ultimate_after"]}}


def _read_flagged_items():
    d = journey.decision()
    h = d["hero"]
    return {"items": [
        {"severity": "amber", "headline": f"AY2023 Commercial Motor reserve revised +€{h['gross_delta']}m gross",
         "detail": f"Net +€{h['net_delta']}m after the 20% quota share; approved.", "id": "SEL-2026Q2-CM-INCURRED"},
        {"severity": "info", "headline": "Duplicate source delivery quarantined",
         "detail": "Re-delivery of the correction batch caught on (claim_id, revision_id); no second €2m.",
         "id": "DLV-2026-07-06-CM-CORR-RETRY"},
        {"severity": "info", "headline": f"Residual finance journal proposed: €{h['residual_to_book']}m",
         "detail": "€2.0m case correction already posted; only the residual IBNR remains to book.", "id": "DEC-2026Q2-CM"},
        {"severity": "info", "headline": "Capital / IFRS 17 dependency identified",
         "detail": "Affected approved inputs flagged for recalculation (no fabricated statutory number).", "id": "handoff"},
    ]}


@router.post("/api/mcp")
async def mcp(request: Request):
    try:
        body = await request.json()
    except Exception:
        return _err(None, -32700, "Parse error")
    i, method, params = body.get("id"), body.get("method"), (body.get("params") or {})
    if method == "initialize":
        return _ok(i, {"protocolVersion": PROTOCOL_VERSION, "serverInfo": SERVER_INFO,
                       "capabilities": {"tools": {}},
                       "instructions": "Connected reserving journey: one claim correction traced through "
                                       "reserve, reinsurance and finance. Read-only."})
    if method in ("notifications/initialized", "notifications/cancelled"):
        return _ok(i, {})
    if method == "tools/list":
        return _ok(i, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        try:
            if name == "read_estimates":
                return _ok(i, _tool_result(_read_estimates()))
            if name == "read_flagged_items":
                return _ok(i, _tool_result(_read_flagged_items()))
            return _err(i, -32601, f"Unknown tool: {name}")
        except Exception as e:
            logger.exception("mcp tool failed")
            return _ok(i, _tool_result({"ok": False, "error": str(e)[:200]}))
    return _err(i, -32601, f"Method not found: {method}")


@router.get("/api/mcp/manifest")
async def manifest():
    return {"server": SERVER_INFO, "protocol_version": PROTOCOL_VERSION,
            "tools": [{"name": t["name"], "description": t["description"]} for t in TOOLS]}
