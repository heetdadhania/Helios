from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.core.sorting import HISTORY_SORT_FIELDS, validate_and_resolve_sort
from app.repositories.history_repository import HistoryRepository
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
from app.schemas.history import AdminHistoryOut, SmbHistoryOut, TeamHistoryOut

router = APIRouter()


@router.get(
    "/mine",
    response_model=PaginatedResponse[SmbHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get SMB Owner Submission History",
    description=(
        "Retrieve customer-facing submission history for the authenticated tenant with server-side pagination. "
        "Surfaces plain-language status (Ready, Processing, Needs attention — please resend) "
        "and generic labels without internal pipeline stage or error jargon."
    ),
)
def get_smb_history(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[SmbHistoryOut]:
    """
    Return the caller's own tenant's submissions only with simplified statuses and server-side pagination.
    """
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to any organization.",
        )

    order_by = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=HISTORY_SORT_FIELDS,
        default_clause="ps.created_at DESC",
    )
    repo = HistoryRepository(cursor)
    raw_history = repo.get_smb_history(
        tenant_id=int(current_user.tenant_id),
        page=page,
        page_size=page_size,
        order_by=order_by,
    )
    if isinstance(raw_history, tuple) and len(raw_history) == 2:
        items, total = raw_history
    else:
        items, total = raw_history, len(raw_history)
    return PaginatedResponse[SmbHistoryOut](
        items=[SmbHistoryOut.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/team",
    response_model=PaginatedResponse[TeamHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get Team Member Submission History",
    description=(
        "Retrieve operational pipeline submission history with server-side pagination. "
        "Team Members see submissions for assigned tenants; Admins see all tenants. "
        "Supports filtering by status and tenant name or ID."
    ),
)
def get_team_history(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter submissions by status"),
    tenant_filter: Optional[str] = Query(None, alias="tenant", description="Filter submissions by tenant business name or ID"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[TeamHistoryOut]:
    """
    Return operational submission history scoped to assigned tenants (or all for Admin) with server-side pagination.
    """
    order_by = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=HISTORY_SORT_FIELDS,
        default_clause="ps.created_at DESC",
    )
    repo = HistoryRepository(cursor)
    raw_history = repo.get_team_history(
        user_id=current_user.id,
        user_role=current_user.role.value,
        status_filter=status_filter,
        tenant_filter=tenant_filter,
        page=page,
        page_size=page_size,
        order_by=order_by,
    )
    if isinstance(raw_history, tuple) and len(raw_history) == 2:
        items, total = raw_history
    else:
        items, total = raw_history, len(raw_history)
    return PaginatedResponse[TeamHistoryOut](
        items=[TeamHistoryOut.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/admin",
    response_model=PaginatedResponse[AdminHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get Admin Submission History",
    description=(
        "Retrieve system-wide submission history including the handling Team Member identity with server-side pagination. "
        "Never scoped to assigned tenants."
    ),
)
def get_admin_history(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter submissions by status"),
    tenant_filter: Optional[str] = Query(None, alias="tenant", description="Filter submissions by tenant business name or ID"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[AdminHistoryOut]:
    """
    Return system-wide submission history explicitly identifying which Team Member handled each batch with server-side pagination.
    """
    order_by = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=HISTORY_SORT_FIELDS,
        default_clause="ps.created_at DESC",
    )
    repo = HistoryRepository(cursor)
    raw_history = repo.get_admin_history(
        status_filter=status_filter,
        tenant_filter=tenant_filter,
        page=page,
        page_size=page_size,
        order_by=order_by,
    )
    if isinstance(raw_history, tuple) and len(raw_history) == 2:
        items, total = raw_history
    else:
        items, total = raw_history, len(raw_history)
    return PaginatedResponse[AdminHistoryOut](
        items=[AdminHistoryOut.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )
