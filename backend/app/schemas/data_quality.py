from typing import Optional
from pydantic import BaseModel, Field


class DataQualityLogOut(BaseModel):
    """Data Quality inspection log item schema matching frontend DataQualityLogItem."""

    id: str = Field(..., description="Unique log entry identifier")
    batch_id: str = Field(..., description="Pipeline execution batch identifier")
    tenant_id: str = Field(..., description="Tenant ID string")
    tenant_name: str = Field(..., description="Tenant business or display name")
    table_name: str = Field(..., description="Target table where rejection occurred")
    rejection_reason: str = Field(..., description="Validation failure explanation")
    timestamp: str = Field(..., description="ISO timestamp of rejection event")
    error_category: Optional[str] = Field(
        None,
        description="Error category (e.g. Schema Drift, Null Threshold Exceeded, Type Mismatch, Duplicate Key)",
    )

    model_config = {"from_attributes": True}
