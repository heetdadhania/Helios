from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    from typing import Any
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.repositories.pipeline_health_repository import PipelineHealthRepository
from app.schemas.auth import UserOut
from app.schemas.pipeline_health import (
    CancelResponse,
    PipelineRunDetailOut,
    PipelineRunOut,
    RestartResponse,
    RetryRequest,
    RetryResponse,
)
from app.services.pipeline_health_service import PipelineHealthService

router = APIRouter()


@router.get(
    "/runs",
    response_model=List[PipelineRunOut],
    status_code=status.HTTP_200_OK,
    summary="List Pipeline Execution Runs",
    description="Retrieve all pipeline runs across tenants. Team Members see assigned tenants; Admins see all.",
)
def list_pipeline_runs(
    status: Optional[str] = Query(None, description="Optional status filter"),
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[PipelineRunOut]:
    """List pipeline execution records with tenant, source, current stage, and status."""
    repo = PipelineHealthRepository(cursor)
    return PipelineHealthService.list_runs(
        current_user=current_user,
        repo=repo,
        status_filter=status,
    )


@router.get(
    "/runs/{batch_id}",
    response_model=PipelineRunDetailOut,
    status_code=status.HTTP_200_OK,
    summary="Get Pipeline Run Detail",
    description="Retrieve detailed history, stage transitions, error message, and linked ETL audit records.",
)
def get_pipeline_run_detail(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> PipelineRunDetailOut:
    """Return stage progression timeline and audit log entries for a single batch."""
    repo = PipelineHealthRepository(cursor)
    return PipelineHealthService.get_run_detail(
        batch_id=batch_id,
        current_user=current_user,
        repo=repo,
    )


@router.post(
    "/runs/{batch_id}/retry-failed-stage",
    response_model=RetryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry Run From Failed Stage",
    description="Trigger Databricks repair-run to re-execute only the failed stage while reusing prior data.",
)
def retry_failed_stage(
    batch_id: str,
    request: Optional[RetryRequest] = None,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> RetryResponse:
    """Repair run from failed stage reusing clean upstream data."""
    repo = PipelineHealthRepository(cursor)
    return PipelineHealthService.retry_from_failed_stage(
        batch_id=batch_id,
        current_user=current_user,
        repo=repo,
        request=request,
    )


@router.post(
    "/runs/{batch_id}/full-restart",
    response_model=RestartResponse,
    status_code=status.HTTP_200_OK,
    summary="Full Restart Ingestion Batch",
    description="Mark batch as restart_required and dispatch a notification requesting the SMB Owner to re-upload.",
)
def full_restart_batch(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> RestartResponse:
    """Instruct re-submission and send alert notification to SMB Owner."""
    repo = PipelineHealthRepository(cursor)
    return PipelineHealthService.full_restart(
        batch_id=batch_id,
        current_user=current_user,
        repo=repo,
    )


@router.post(
    "/runs/{batch_id}/cancel",
    response_model=CancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Pipeline Run",
    description="Cancel an actively running pipeline run.",
)
def cancel_pipeline_run(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> CancelResponse:
    """Request clean cancellation of an actively running pipeline batch."""
    repo = PipelineHealthRepository(cursor)
    return PipelineHealthService.cancel_run(
        batch_id=batch_id,
        current_user=current_user,
        repo=repo,
    )

