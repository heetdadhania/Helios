from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore
from app.core.dependencies import get_current_active_user, get_db_cursor
from app.schemas.dataset import (
    ColumnSchema,
    DataCleanRequest,
    DataCleanResponse,
    DatasetInspectRequest,
    DatasetResponse,
)
from app.services.cleaning_service import CleaningService
from app.services.connector_service import DatabricksConnectorService
from app.services.schema_inference_service import SchemaInferenceService

router = APIRouter()


@router.get("/tables", response_model=List[Dict[str, Any]])
def list_delta_tables(
    catalog: Optional[str] = Query(None, description="Unity Catalog override"),
    schema: Optional[str] = Query(None, description="Schema/database override"),
    cursor: Cursor = Depends(get_db_cursor),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List Delta Lake tables available in Databricks Unity Catalog."""
    service = DatabricksConnectorService(cursor)
    return service.list_catalog_tables(catalog=catalog, schema=schema)


@router.post("/inspect", response_model=DatasetResponse)
def inspect_delta_table(
    inspect_in: DatasetInspectRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> DatasetResponse:
    """Inspect schema and row count for a Delta Lake table in Unity Catalog."""
    service = DatabricksConnectorService(cursor)
    return service.inspect_table(
        table_name=inspect_in.table_name,
        catalog=inspect_in.catalog,
        schema_name=inspect_in.schema_name,
    )


@router.post("/clean", response_model=DataCleanResponse)
def clean_records(
    clean_in: DataCleanRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> DataCleanResponse:
    """Execute data cleaning rules, trimming strings and imputing null values."""
    return CleaningService.clean_dataset(clean_in)


@router.post("/infer-schema", response_model=List[ColumnSchema])
def infer_schema_from_records(
    records: List[Dict[str, Any]],
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> List[ColumnSchema]:
    """Infer column data types and nullability from raw tabular dictionary records."""
    return SchemaInferenceService.infer_from_records(records)
