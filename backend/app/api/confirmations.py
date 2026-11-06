from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.repositories.confirmation_repository import ConfirmationRepository
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
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
from app.core.sorting import PENDING_UPLOADS_SORT_FIELDS, validate_and_resolve_sort

router = APIRouter()


@router.get(
    "/pending",
    response_model=PaginatedResponse[PendingUploadOut],
    status_code=status.HTTP_200_OK,
    summary="Get Pending Ingestion Batches",
    description="Retrieve batches awaiting schema confirmation with server-side pagination. Scoped to assigned tenants for Team Members, all tenants for Admins. SMB Owners are forbidden.",
)
def get_pending_uploads(
    tenant_id: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Sort field: date, organization, source, status"),
    sort_order: Optional[str] = Query(None, description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[PendingUploadOut]:
    """
    List pending batches requiring review with server-side pagination. Includes source_type (upload, db_connection).
    """
    order_by_sql = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=PENDING_UPLOADS_SORT_FIELDS,
        default_clause="ps.created_at DESC",
    )
    repo = ConfirmationRepository(cursor)
    return ConfirmationService.get_pending_uploads(
        current_user=current_user,
        repo=repo,
        tenant_filter=tenant_id,
        page=page,
        page_size=page_size,
        order_by=order_by_sql,
    )


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
