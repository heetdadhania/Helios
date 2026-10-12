from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PendingUploadOut(BaseModel):
    """Represents a Bronze-ingested batch awaiting schema confirmation by Team Member / Admin."""

    batch_id: str = Field(..., description="Unique ingestion batch UUID")
    tenant_id: int = Field(..., description="ID of the tenant data owner")
    tenant_name: Optional[str] = Field(None, description="Display name of the tenant")
    upload_id: Optional[int] = Field(None, description="Optional foreign key to platform.pending_uploads")
    source_type: str = Field("upload", description="Ingestion channel: upload, db_connection, api_push")
    filename: Optional[str] = Field("upload.data", description="Original filename")
    file_size_bytes: Optional[int] = Field(None, description="Size of file in bytes")
    row_count: Optional[int] = Field(0, description="Estimated or loaded row count")
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
    internal_notes: Optional[str] = Field(
        default=None,
        description="Optional internal notes recorded during schema confirmation",
    )
    unmapped_required_fields: List[str] = Field(
        default_factory=list,
        description="List of required canonical fields not mapped in the incoming dataset",
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
    internal_notes: Optional[str] = Field(
        default=None,
        description="Optional internal reviewer notes or audit comments recorded during confirmation",
    )


class ConfirmResponse(BaseModel):
    """Response returned upon successfully confirming schema and transitioning to Silver."""

    batch_id: str = Field(..., description="Confirmed batch UUID")
    status: str = Field("silver_running", description="New pipeline status")
    confirmed_template: str = Field(..., description="Confirmed template name")
    message: str = Field(..., description="Human-readable confirmation message")


class CompletenessResponse(BaseModel):
    """Data completeness indicator metrics for an ingestion batch after Silver cleaning."""

    total_rows: int = Field(..., description="Total rows ingested into Bronze for this batch")
    accepted_rows: int = Field(..., description="Rows successfully written to the Silver clean table")
    rejected_rows: int = Field(..., description="Rows rejected during Silver validation and logged in meta.data_quality_log")
    completeness_percentage: float = Field(..., description="Completeness percentage: (accepted_rows / total_rows) * 100")

    model_config = {"from_attributes": True}


class RejectRequest(BaseModel):
    """Payload for rejecting an ingestion batch."""

    reason: str = Field(..., min_length=5, description="Mandatory reason explaining batch rejection (min 5 chars)")


class RejectResponse(BaseModel):
    """Response returned upon rejecting an ingestion batch."""

    batch_id: str
    status: str
    message: str
    reason: str
