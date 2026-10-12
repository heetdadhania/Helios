from typing import Any, List
from fastapi import APIRouter, Depends, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.repositories.confirmation_repository import ConfirmationRepository
from app.schemas.auth import UserOut
from app.schemas.confirmation import (
    CompletenessResponse,
    ConfirmRequest,
    ConfirmResponse,
    PendingUploadOut,
    RejectRequest,
    RejectResponse,
    SchemaPreviewOut,
)
from app.services.confirmation_service import ConfirmationService

router = APIRouter()


@router.get(
    "/pending",
    response_model=List[PendingUploadOut],
    status_code=status.HTTP_200_OK,
    summary="Get Pending Ingestion Batches",
    description="Retrieve batches awaiting schema confirmation. Scoped to assigned tenants for Team Members, all tenants for Admins. SMB Owners are forbidden.",
)
def get_pending_uploads(
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[PendingUploadOut]:
    """
    List pending batches requiring review. Includes source_type (upload, db_connection, api_push).
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.get_pending_uploads(current_user=current_user, repo=repo)


@router.get(
    "/{batch_id}/preview",
    response_model=SchemaPreviewOut,
    status_code=status.HTTP_200_OK,
    summary="Preview Inferred Schema and Sample Rows",
    description="Inspect detected template, confidence score, source type, column mappings, sample Bronze rows, and internal notes.",
)
def get_schema_preview(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> SchemaPreviewOut:
    """
    Retrieve preview data and internal notes for a specific pending batch.
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.get_preview(batch_id=batch_id, current_user=current_user, repo=repo)


@router.post(
    "/{batch_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or Correct Schema Mapping",
    description="Approve schema mapping with optional corrections and internal notes, record confirmation audit, and trigger Silver pipeline stage.",
)
def confirm_schema_mapping(
    batch_id: str,
    request: ConfirmRequest,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> ConfirmResponse:
    """
    Confirm inferred schema for a batch, persist optional reviewer notes, and trigger the Silver stage.
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.confirm_mapping(
        batch_id=batch_id,
        request=request,
        current_user=current_user,
        repo=repo,
    )


@router.post(
    "/{batch_id}/reject",
    response_model=RejectResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Ingestion Batch",
    description="Reject pending batch with mandatory explanation (min 5 chars), leaving Bronze data intact and recording audit trail.",
)
def reject_batch(
    batch_id: str,
    request: RejectRequest,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> RejectResponse:
    """
    Reject an ingestion batch with a reason. Leaves Bronze data in place and removes batch from pending list.
    """
    repo = ConfirmationRepository(cursor)
    res = ConfirmationService.reject_batch(
        batch_id=batch_id,
        reason=request.reason,
        current_user=current_user,
        repo=repo,
    )
    return RejectResponse(**res)


@router.get(
    "/{batch_id}/completeness",
    response_model=CompletenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Data Completeness Indicator",
    description="Calculate and return the completeness indicator for a batch after Silver stage processing.",
)
def get_data_completeness(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> CompletenessResponse:
    """
    Calculate and return: (rows successfully written to Silver) / (total rows ingested into Bronze) as a percentage.
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.get_completeness(batch_id=batch_id, current_user=current_user, repo=repo)
