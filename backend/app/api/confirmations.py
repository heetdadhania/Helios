from typing import List
from fastapi import APIRouter, Depends, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.repositories.confirmation_repository import ConfirmationRepository
from app.schemas.auth import UserOut
from app.schemas.confirmation import (
    ConfirmRequest,
    ConfirmResponse,
    PendingUploadOut,
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
    description="Inspect detected template, confidence score, source type, column mappings, and sample Bronze rows.",
)
def get_schema_preview(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> SchemaPreviewOut:
    """
    Retrieve preview data for a specific pending batch.
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.get_preview(batch_id=batch_id, current_user=current_user, repo=repo)


@router.post(
    "/{batch_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or Correct Schema Mapping",
    description="Approve schema mapping with optional corrections, record confirmation audit, and trigger Silver pipeline stage.",
)
def confirm_schema_mapping(
    batch_id: str,
    request: ConfirmRequest,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> ConfirmResponse:
    """
    Confirm inferred schema for a batch and trigger the Silver stage.
    """
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.confirm_mapping(
        batch_id=batch_id,
        request=request,
        current_user=current_user,
        repo=repo,
    )
