from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Specification of an inferred or confirmed column in a Delta Lake table."""

    name: str
    data_type: str
    nullable: bool = True
    comment: Optional[str] = None


class DatasetInspectRequest(BaseModel):
    """Request payload to inspect a Unity Catalog Delta Lake table."""

    table_name: str = Field(..., description="Target Delta table name")
    catalog: Optional[str] = Field(None, description="Unity Catalog override")
    schema_name: Optional[str] = Field(None, description="Schema/database override")


class DatasetResponse(BaseModel):
    """Details of inspected Delta table in Databricks Unity Catalog."""

    table_name: str
    catalog: str
    schema_name: str
    columns: List[ColumnSchema]
    total_rows: Optional[int] = None
    table_type: Optional[str] = None


class DataCleanRequest(BaseModel):
    """Specification for cleaning and sanitizing tabular records."""

    records: List[Dict[str, Any]] = Field(..., description="List of raw row dictionaries")
    strip_whitespace: bool = True
    impute_nulls: bool = True
    null_value_replacements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom default value replacements for specified columns",
    )


class DataCleanResponse(BaseModel):
    """Result of data cleaning execution."""

    cleaned_records: List[Dict[str, Any]]
    total_processed: int
    null_counts_imputed: Dict[str, int]
