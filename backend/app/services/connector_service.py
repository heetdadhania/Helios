from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore
from app.core.config import settings
from app.repositories.query_repo import QueryRepository
from app.schemas.dataset import DatasetResponse
from app.services.schema_inference_service import SchemaInferenceService


class DatabricksConnectorService:
    """Service orchestrating interactions with Databricks Unity Catalog and Delta Lake."""

    def __init__(self, cursor: Cursor) -> None:
        self.cursor = cursor
        self.query_repo = QueryRepository(cursor)

    def get_effective_catalog_schema(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> tuple[str, str]:
        """Determine target catalog and schema using defaults if not provided."""
        target_catalog = catalog or settings.DATABRICKS_CATALOG
        target_schema = schema or settings.DATABRICKS_SCHEMA
        return target_catalog, target_schema

    def list_catalog_tables(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available Delta Lake tables in specified or default Unity Catalog."""
        cat, sch = self.get_effective_catalog_schema(catalog, schema)
        return self.query_repo.list_tables(cat, sch)

    def inspect_table(
        self,
        table_name: str,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> DatasetResponse:
        """Introspect table structure, column types, and row count from Unity Catalog."""
        cat, sch = self.get_effective_catalog_schema(catalog, schema)
        describe_rows = self.query_repo.describe_table(cat, sch, table_name)
        columns = SchemaInferenceService.parse_databricks_describe(describe_rows)
        total_rows = self.query_repo.count_table_rows(cat, sch, table_name)

        return DatasetResponse(
            table_name=table_name,
            catalog=cat,
            schema_name=sch,
            columns=columns,
            total_rows=total_rows,
            table_type="delta",
        )

    def preview_table_data(
        self,
        table_name: str,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch sample row data from a Delta table."""
        cat, sch = self.get_effective_catalog_schema(catalog, schema)
        return self.query_repo.sample_table_data(cat, sch, table_name, limit=limit)
