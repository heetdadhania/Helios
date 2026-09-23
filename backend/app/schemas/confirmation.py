from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PendingUploadOut(BaseModel):
    """Represents a Bronze-ingested batch awaiting schema confirmation by Team Member / Admin."""

    batch_id: str = Field(..., description="Unique ingestion batch UUID")
    tenant_id: int = Field(..., description="ID of the tenant data owner")
    upload_id: Optional[int] = Field(None, description="Optional foreign key to platform.pending_uploads")
    source_type: str = Field("upload", description="Ingestion channel: upload, db_connection, api_push")
    stage: str = Field("schema_inference", description="Current pipeline stage")
    status: str = Field("awaiting_confirmation", description="Current pipeline status")
    detected_template: Optional[str] = Field(None, description="Inferred template name (e.g. template_orders)")
    confidence_score: Optional[float] = Field(None, description="Inference engine confidence rating (0.0 to 1.0)")
    created_at: Optional[datetime] = Field(None, description="Timestamp batch was initiated")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last state modification")

    model_config = {"from_attributes": True}


class SchemaPreviewOut(BaseModel):
    """Detailed schema preview and sample rows for Team Member / Admin review."""

    batch_id: str = Field(..., description="Unique ingestion batch UUID")
    tenant_id: int = Field(..., description="ID of the tenant data owner")
    detected_template: str = Field(..., description="Inferred canonical template name")
    confidence_score: float = Field(..., description="Inference engine confidence score")
    source_type: str = Field("upload", description="Ingestion channel (upload, db_connection, api_push)")
    column_mapping: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed mapping of source columns to canonical target fields and inferred data types",
    )
    sample_rows: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sample records from Bronze layer for preview",
    )

    model_config = {"from_attributes": True}


class ConfirmRequest(BaseModel):
    """Payload to confirm or correct the schema mapping for a batch."""

    confirmed_template: str = Field(
        ...,
        description="Target canonical template confirmed by reviewer (e.g. template_orders, template_shipping)",
    )
    corrected_mapping: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional reviewer-modified column mapping dictionary overriding inferred mappings",
    )


class ConfirmResponse(BaseModel):
    """Response returned upon successfully confirming schema and transitioning to Silver."""

    batch_id: str = Field(..., description="Confirmed batch UUID")
    status: str = Field("silver_running", description="New pipeline status")
    confirmed_template: str = Field(..., description="Confirmed template name")
    message: str = Field(..., description="Human-readable confirmation message")
