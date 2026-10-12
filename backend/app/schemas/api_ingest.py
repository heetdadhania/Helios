from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_RECORDS_PER_PAYLOAD = 10000


class ApiIngestPayload(BaseModel):
    """Payload for programmatic push ingestion containing order/shipping records."""

    records: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=MAX_RECORDS_PER_PAYLOAD,
        description=f"Array of JSON records (max {MAX_RECORDS_PER_PAYLOAD} per request)",
    )
    override_duplicate: bool = Field(
        default=False,
        description="Whether to override duplicate submission check",
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Audit reason for duplicate override (min 5 characters)",
    )

    @field_validator("records")
    @classmethod
    def validate_records(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure records are non-empty dictionaries with valid tabular keys."""
        if not v:
            raise ValueError("records list cannot be empty.")
        for idx, record in enumerate(v):
            if not isinstance(record, dict) or not record:
                raise ValueError(f"Record at index {idx} must be a non-empty JSON object.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "records": [
                    {
                        "order_id": "ORD-5012",
                        "customer_id": "CUST-992",
                        "amount": 149.99,
                        "status": "shipped",
                        "tracking_number": "TRK992144512",
                        "ordered_at": "2026-09-23T10:15:00Z",
                    },
                    {
                        "order_id": "ORD-5013",
                        "customer_id": "CUST-104",
                        "amount": 79.50,
                        "status": "pending",
                        "tracking_number": None,
                        "ordered_at": "2026-09-23T10:30:00Z",
                    },
                ]
            }
        }
    )


class ApiIngestResponse(BaseModel):
    """Response returned upon successful receipt and Bronze landing of API push batch."""

    batch_id: str = Field(..., description="UUID identifying the ETL batch across the medallion pipeline")
    status: str = Field(..., description="Initial ingestion state (e.g. ingested)")
    records_received: int = Field(..., description="Total count of records accepted for ingestion")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "8f489f62-3c1a-4d22-8e12-b912a524a83e",
                "status": "ingested",
                "records_received": 2,
            }
        }
    )


class ApiKeyOut(BaseModel):
    """Customer-facing API key info. Masked key representation only; raw key never stored."""

    api_key_id: int = Field(..., description="Unique API key identifier")
    tenant_id: int = Field(..., description="Tenant organization ID")
    masked_key: str = Field(..., description="Masked key preview (e.g. helios_live_••••1a2b)")
    created_at: Optional[datetime] = Field(None, description="Timestamp when key was issued")
    last_used_at: Optional[datetime] = Field(None, description="Timestamp of last authenticated ingestion")
    is_active: bool = Field(True, description="Active status flag")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": 1,
                "tenant_id": 42,
                "masked_key": "helios_live_••••1a2b",
                "created_at": "2026-09-23T12:00:00Z",
                "last_used_at": "2026-09-23T14:30:00Z",
                "is_active": True,
            }
        }
    )


class ApiKeyGeneratedOut(BaseModel):
    """Returned only once at generation time containing the raw API key."""

    api_key_id: int = Field(..., description="Unique API key identifier")
    tenant_id: int = Field(..., description="Tenant organization ID")
    api_key: str = Field(..., description="Full raw API key. Shown ONLY ONCE at generation time")
    masked_key: str = Field(..., description="Masked key representation for persistent display")
    created_at: datetime = Field(..., description="Creation timestamp")
    message: str = Field(
        default="API key generated successfully. Save this key now; it will not be displayed again.",
        description="Security guidance notice",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": 1,
                "tenant_id": 42,
                "api_key": "helios_live_dGVzdF9zZWNyZXRfa2V5XzEyMzQ1Njc4OQ",
                "masked_key": "helios_live_••••6789",
                "created_at": "2026-09-23T12:00:00Z",
                "message": "API key generated successfully. Save this key now; it will not be displayed again.",
            }
        }
    )
