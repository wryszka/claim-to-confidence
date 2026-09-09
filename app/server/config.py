"""Config — all portability via env vars (set in app.yaml). No hardcoded catalog/schema/IDs."""
import os
from functools import lru_cache

from databricks.sdk import WorkspaceClient

CATALOG = os.getenv("CATALOG_NAME", "lr_dev_aws_us_catalog")
SCHEMA = os.getenv("SCHEMA_NAME", "claim_to_confidence")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "a3b61648ea4809e3")
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-sonnet-5")
ENTITY = os.getenv("ENTITY_NAME", "Bricksurance SE")
HUB_APP_URL = os.getenv("HUB_APP_URL", "")


def fqn(table: str) -> str:
    return f"{CATALOG}.{SCHEMA}.`{table}`"


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    return WorkspaceClient()
