"""Thin SQL helper — runs statements on the warehouse via the app service principal.

Raises on a failed statement so a silently-swallowed failure (e.g. a missing grant)
never lets an endpoint report success while nothing was read. Values return as strings
from the API — cast in callers."""
from concurrent.futures import ThreadPoolExecutor
from . import config

_POOL = ThreadPoolExecutor(max_workers=8)


def query(statement: str):
    w = config.get_workspace_client()
    resp = w.statement_execution.execute_statement(
        statement=statement, warehouse_id=config.WAREHOUSE_ID,
        catalog=config.CATALOG, schema=config.SCHEMA, wait_timeout="50s")
    state = resp.status.state.value if (resp.status and resp.status.state) else "UNKNOWN"
    if state != "SUCCEEDED":
        msg = (resp.status.error.message if (resp.status and resp.status.error) else state)
        raise RuntimeError(f"SQL {state}: {msg}")
    result = resp.result
    if result is None or result.data_array is None:
        return []
    cols = [c.name for c in resp.manifest.schema.columns]
    return [dict(zip(cols, row)) for row in result.data_array]


def query_one(statement: str):
    rows = query(statement)
    return rows[0] if rows else None


def query_many(statements: dict):
    def _safe(s):
        try:
            return query(s)
        except Exception:
            return []
    futures = {k: _POOL.submit(_safe, s) for k, s in statements.items()}
    return {k: f.result() for k, f in futures.items()}


def esc(s: str) -> str:
    return (s or "").replace("'", "''")
