from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Payload returned immediately upon successful file ingestion initiation."""

    upload_id: int = Field(..., description="Unique ID of the pending upload record")
    batch_id: str = Field(..., description="UUID identifying the ETL batch across the medallion pipeline")
    status: str = Field(..., description="Initial ingestion state")

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_id": 42,
                "batch_id": "9f3f9f71-6c1d-4bc5-9c59-b1d7d512a83e",
                "status": "pending",
            }
        }
    }


class UploadStatusOut(BaseModel):
    """Simplified status output presented to SMB Owners without exposing pipeline internals."""

    batch_id: str = Field(..., description="ETL batch UUID")
    stage: str = Field(..., description="Plain-language stage indicator: Processing, Ready, or Failed")
    status: str = Field(..., description="Human-friendly message: 'Processing', 'Ready', or 'Failed — please check your file and try again'")
    updated_at: datetime = Field(..., description="Timestamp of the latest status modification")

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "9f3f9f71-6c1d-4bc5-9c59-b1d7d512a83e",
                "stage": "Processing",
                "status": "Processing",
                "updated_at": "2026-09-22T17:45:00Z",
            }
        }
    }
