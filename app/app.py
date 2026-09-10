"""
Claim to Confidence — FastAPI backend. Serves the single-page app and the journey
endpoints. Every business number is computed live from the Unity Catalog scenario tables
through the pure engine (server/engine.py) — the acceptance tests prove that engine to
the cent. No reserve outcome is computed in the browser.
"""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from server import journey, agent, mcp

app = FastAPI(title="Claim to Confidence")
DIST = os.path.join(os.path.dirname(__file__), "dist")


def _safe(fn, *a, **k):
    try:
        return JSONResponse(fn(*a, **k))
    except Exception as e:  # surface the real error honestly, never a fake success
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/meta")
def api_meta():
    return _safe(journey.meta)


@app.get("/api/decision")
def api_decision():
    return _safe(journey.decision)


@app.get("/api/readiness")
def api_readiness():
    return _safe(journey.readiness)


@app.get("/api/practitioner")
def api_practitioner():
    return _safe(journey.practitioner)


@app.get("/api/change-impact")
def api_change_impact():
    return _safe(journey.change_impact)


@app.get("/api/finance")
def api_finance():
    return _safe(journey.finance)


@app.get("/api/review")
def api_review():
    return _safe(journey.review)


@app.get("/api/evidence")
def api_evidence():
    return _safe(journey.evidence)


@app.get("/api/downstream")
def api_downstream():
    return _safe(journey.downstream)


@app.get("/api/lineage")
def api_lineage():
    return _safe(journey.lineage)


@app.get("/api/committee-report")
def api_committee_report():
    return _safe(journey.committee_report)


@app.get("/api/reproduce")
def api_reproduce():
    return _safe(journey.reproduce)


@app.get("/api/selection/recompute")
def api_recompute(cl_weight: float = Query(..., ge=0.0, le=1.0)):
    return _safe(journey.recompute, cl_weight)


@app.get("/api/agent/suggested")
def api_agent_suggested():
    return JSONResponse({"suggested": agent.SUGGESTED})


@app.get("/api/agent/ask")
def api_agent_ask(q: str = Query(...), notes: bool = Query(False)):
    return _safe(agent.ask, q, notes)


@app.get("/api/agent/attempt")
def api_agent_attempt(action: str = Query(...)):
    return _safe(agent.attempt_privileged_action, action)


@app.get("/api/agent/trace")
def api_agent_trace():
    return _safe(agent.ai_trace)


app.include_router(mcp.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(os.path.join(DIST, "index.html"))
