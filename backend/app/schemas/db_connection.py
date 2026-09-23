from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


SupportedDbType = Literal["mysql", "postgresql", "sqlserver"]

DEFAULT_DB_PORTS = {
    "mysql": 3306,
    "postgresql": 5432,
    "sqlserver": 1433,
}


class DbConnectionBase(BaseModel):
    """Base fields for database connection configuration."""

    db_type: SupportedDbType = Field(
        ...,
        description="Target RDBMS engine type: 'mysql', 'postgresql', or 'sqlserver'",
    )
    host: str = Field(..., min_length=1, max_length=255, description="Database server hostname or IP address")
    port: int = Field(..., ge=1, le=65535, description="Database listener port number")
    database_name: str = Field(..., min_length=1, max_length=128, description="Target database/catalog name")
    username: str = Field(..., min_length=1, max_length=128, description="Database service user identifier")
    table_or_query: str = Field(
        ...,
        min_length=1,
        description="Target table name, view name, or custom SELECT query to extract",
    )
    is_active: bool = Field(default=True, description="Flag indicating if connection is active")

    @field_validator("db_type", mode="before")
    @classmethod
    def normalize_db_type(cls, v: str) -> str:
        """Normalize engine identifier to lowercase."""
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("postgres", "pgsql"):
                return "postgresql"
            if val in ("mssql", "sql_server", "microsoft_sql_server"):
                return "sqlserver"
            return val
        return v

    @field_validator("table_or_query")
    @classmethod
    def validate_table_or_query(cls, v: str) -> str:
        """Validate query or table identifier."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("table_or_query cannot be empty.")
        return cleaned


class DbConnectionCreate(DbConnectionBase):
    """Payload to create or test a database connection containing raw credentials."""

    password: str = Field(
        ...,
        min_length=1,
        description="Raw database authentication password (NEVER persisted directly in platform tables)",
        repr=False,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "db_type": "postgresql",
                "host": "db.acme.example.com",
                "port": 5432,
                "database_name": "sales_db",
                "username": "helios_reader",
                "password": "strongPassword123!",
                "table_or_query": "orders",
                "is_active": True,
            }
        }
    )


class DbConnectionOut(BaseModel):
    """Public customer-facing database connection details. Never exposes passwords or secret references."""

    connection_id: int = Field(..., description="Unique database connection identifier")
    tenant_id: int = Field(..., description="Owning tenant identifier")
    db_type: str = Field(..., description="Engine type: mysql, postgresql, or sqlserver")
    host: str = Field(..., description="Server hostname or IP")
    port: int = Field(..., description="Server listener port")
    database_name: str = Field(..., description="Database name")
    username: str = Field(..., description="Service username")
    table_or_query: str = Field(..., description="Table name or SQL extraction query")
    last_synced_at: Optional[datetime] = Field(None, description="Timestamp of last successful data sync")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    is_active: bool = Field(True, description="Active status flag")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "connection_id": 1,
                "tenant_id": 42,
                "db_type": "postgresql",
                "host": "db.acme.example.com",
                "port": 5432,
                "database_name": "sales_db",
                "username": "helios_reader",
                "table_or_query": "orders",
                "last_synced_at": "2026-09-23T12:00:00Z",
                "created_at": "2026-09-23T11:00:00Z",
                "is_active": True,
            }
        },
    )


class DbConnectionTestResult(BaseModel):
    """Result of connection verification test."""

    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Status message without leaking sensitive credentials")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Connection verified successfully.",
            }
        }
    )


class DbConnectionSyncResponse(BaseModel):
    """Response payload returned when initiating an on-demand database sync."""

    connection_id: int = Field(..., description="Connection ID synced")
    upload_id: int = Field(..., description="Unique ID of created pending upload tracking record")
    batch_id: str = Field(..., description="UUID identifying the ETL batch across the medallion pipeline")
    status: str = Field(..., description="Current status of the ingestion pipeline")
    rows_synced: int = Field(..., description="Number of rows extracted from the source database")
    message: str = Field(..., description="Summary status message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "connection_id": 1,
                "upload_id": 42,
                "batch_id": "9f3f9f71-6c1d-4bc5-9c59-b1d7d512a83e",
                "status": "ingested",
                "rows_synced": 1250,
                "message": "Extracted 1250 rows and queued for Medallion Bronze ingestion.",
            }
        }
    )
