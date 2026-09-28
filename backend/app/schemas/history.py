from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SmbHistoryOut(BaseModel):
    """
    Plain-language submission history entry for SMB Owner view.
    Surfaces minimal non-technical details: date, user-friendly status, and generic label.
    """

    batch_id: str = Field(..., description="Unique submission batch identifier")
    date: str = Field(..., description="Submission date / timestamp (e.g. YYYY-MM-DD HH:MM:SS)")
    status: str = Field(..., description="Plain-language status: 'Ready', 'Processing', or 'Needs attention — please resend'")
    label: str = Field("Data received", description="User-facing submission label without technical jargon")

    model_config = {"from_attributes": True}


class TeamHistoryOut(BaseModel):
    """
    Operational submission history entry for Team Member view.
    Surfaces operational pipeline details: tenant, source_type, stage, status, error details, timestamp.
    """

    batch_id: str = Field(..., description="Unique pipeline execution batch identifier")
    tenant_id: int = Field(..., description="ID of the tenant data owner")
    tenant: str = Field(..., description="Business name of the tenant organization")
    source_type: str = Field("upload", description="Ingestion method (upload, api_push, db_connection)")
    stage: str = Field(..., description="Pipeline stage: bronze_ingest, schema_inference, silver_clean, gold_transform")
    status: str = Field(..., description="Operational status: ingested, awaiting_confirmation, silver_running, gold_running, success, failed")
    error_message: Optional[str] = Field(None, description="Detailed error stack or failure reason if failed")
    timestamp: datetime = Field(..., description="Batch submission/initiation timestamp")

    model_config = {"from_attributes": True}


class AdminHistoryOut(TeamHistoryOut):
    """
    System-wide submission history entry for Admin view.
    Inherits all operational detail from TeamHistoryOut and explicitly surfaces which Team Member handled the batch.
    """

    handled_by: str = Field("N/A", description="Name of the Team Member who handled/initiated the batch, or 'N/A' if Admin")
