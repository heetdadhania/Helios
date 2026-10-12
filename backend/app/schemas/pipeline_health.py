from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PipelineRunOut(BaseModel):
    """Summary of a pipeline run visible to Team Members and Admins."""

    batch_id: str = Field(..., description="Unique pipeline execution batch UUID")
    tenant_id: int = Field(..., description="ID of the tenant data owner")
    tenant: Optional[str] = Field(None, description="Business name or display label of tenant")
    tenant_name: Optional[str] = Field(None, description="Business name of tenant")
    source_type: str = Field("upload", description="Ingestion channel: upload, db_connection, api_push")
    current_stage: str = Field(..., description="Current or stopped stage of execution")
    status: str = Field(..., description="Pipeline execution state")
    started_at: Optional[datetime] = Field(None, description="Batch initiation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last status modification timestamp")
    error_message: Optional[str] = Field(None, description="Failure reason if run stopped")
    failed_stage: Optional[str] = Field(None, description="Stage where pipeline execution failed")
    failure_message: Optional[str] = Field(None, description="Detailed error message")
    failure_next_step: Optional[str] = Field(None, description="Remediation next step")

    model_config = {"from_attributes": True}


class EtlAuditLogOut(BaseModel):
    """Detailed audit log entry from meta.etl_audit_log."""

    log_id: Optional[int] = Field(None, description="Unique audit log entry identifier")
    batch_id: str = Field(..., description="Batch identifier")
    stage: str = Field(..., description="ETL stage: bronze_ingest, silver_clean, gold_transform")
    row_count: Optional[int] = Field(None, description="Rows processed in this stage execution")
    status: str = Field(..., description="Stage status: started, completed, failed")
    started_at: Optional[datetime] = Field(None, description="Stage start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Stage completion timestamp")
    error_message: Optional[str] = Field(None, description="Stage error message if failed")

    model_config = {"from_attributes": True}


class StageHistoryItem(BaseModel):
    """Chronological progression entry for an ETL stage execution."""

    stage: str = Field(..., description="Pipeline stage name")
    status: str = Field(..., description="Stage completion or failure state")
    started_at: Optional[datetime] = Field(None, description="Stage start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Stage finish timestamp")
    duration_seconds: Optional[float] = Field(None, description="Execution duration in seconds")
    row_count: Optional[int] = Field(None, description="Records processed")
    error_message: Optional[str] = Field(None, description="Error details if stage failed")

    model_config = {"from_attributes": True}


class PipelineRunDetailOut(PipelineRunOut):
    """Full detail of a pipeline run including stage progression and audit log items."""

    stage_history: List[StageHistoryItem] = Field(default_factory=list, description="Stage timeline")
    audit_logs: List[EtlAuditLogOut] = Field(default_factory=list, description="Linked audit entries")


class RetryRequest(BaseModel):
    """Optional parameters passed when triggering a stage repair run."""

    rerun_tasks: Optional[List[str]] = Field(None, description="Explicit task names to re-run")
    reason: Optional[str] = Field(None, description="Reason for triggering stage repair")


class RetryResponse(BaseModel):
    """Response returned after initiating a repair-run for failed tasks."""

    batch_id: str = Field(..., description="Repaired batch identifier")
    status: str = Field(..., description="Updated pipeline status")
    current_stage: str = Field(..., description="Stage being re-executed")
    message: str = Field(..., description="Human-readable repair outcome message")
    repaired_tasks: Optional[List[str]] = Field(None, description="Tasks queued for execution")


class RestartResponse(BaseModel):
    """Response returned when marking a batch for complete re-submission."""

    batch_id: str = Field(..., description="Batch identifier marked for restart")
    status: str = Field("restart_required", description="Pipeline status")
    message: str = Field(..., description="Instructions detailing required re-upload")
    notification_sent: bool = Field(True, description="Whether SMB Owner was notified")


class CancelResponse(BaseModel):
    """Response returned when cancelling a running batch."""

    batch_id: str = Field(..., description="Batch identifier cancelled")
    status: str = Field("cancelled", description="Pipeline status")
    message: str = Field(..., description="Cancellation outcome message")

