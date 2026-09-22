from typing import Any, Dict
from fastapi import APIRouter, status
from app.core.config import settings
from app.db.base import check_databricks_connection

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, Any]:
    """Return health status of the Helios API service."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/databricks", status_code=status.HTTP_200_OK)
def databricks_health_check() -> Dict[str, Any]:
    """Verify live connectivity to Databricks Free Edition / Unity Catalog endpoint."""
    is_connected = check_databricks_connection()
    return {
        "status": "connected" if is_connected else "disconnected",
        "databricks_hostname": settings.DATABRICKS_SERVER_HOSTNAME,
        "catalog": settings.DATABRICKS_CATALOG,
        "schema": settings.DATABRICKS_SCHEMA,
    }
