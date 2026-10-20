from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.history_repository import HistoryRepository
from app.schemas.auth import UserOut
from app.schemas.history import AdminHistoryOut, SmbHistoryOut, TeamHistoryOut

router = APIRouter()


@router.get(
    "/mine",
    response_model=List[SmbHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get SMB Owner Submission History",
    description=(
        "Retrieve customer-facing submission history for the authenticated tenant. "
        "Surfaces plain-language status (Ready, Processing, Needs attention — please resend) "
        "and generic labels without internal pipeline stage or error jargon."
    ),
)
def get_smb_history(
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[SmbHistoryOut]:
    """
    Return the caller's own tenant's submissions only with simplified statuses.
    """
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to any organization.",
        )

    repo = HistoryRepository(cursor)
    raw_history = repo.get_smb_history(tenant_id=int(current_user.tenant_id))
    return [SmbHistoryOut.model_validate(r) for r in raw_history]


@router.get(
    "/team",
    response_model=List[TeamHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get Team Member Submission History",
    description=(
        "Retrieve operational pipeline submission history. "
        "Team Members see submissions for assigned tenants; Admins see all tenants. "
        "Supports filtering by status and tenant name or ID."
    ),
)
def get_team_history(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter submissions by status"),
    tenant_filter: Optional[str] = Query(None, alias="tenant", description="Filter submissions by tenant business name or ID"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[TeamHistoryOut]:
    """
    Return operational submission history scoped to assigned tenants (or all for Admin).
    """
    repo = HistoryRepository(cursor)
    raw_history = repo.get_team_history(
        user_id=current_user.id,
        user_role=current_user.role.value,
        status_filter=status_filter,
        tenant_filter=tenant_filter,
    )
    return [TeamHistoryOut.model_validate(r) for r in raw_history]


@router.get(
    "/admin",
    response_model=List[AdminHistoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get Admin Submission History",
    description=(
        "Retrieve system-wide submission history including the handling Team Member identity. "
        "Never scoped to assigned tenants."
    ),
)
def get_admin_history(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter submissions by status"),
    tenant_filter: Optional[str] = Query(None, alias="tenant", description="Filter submissions by tenant business name or ID"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[AdminHistoryOut]:
    """
    Return system-wide submission history explicitly identifying which Team Member handled each batch.
    """
    repo = HistoryRepository(cursor)
    raw_history = repo.get_admin_history(
        status_filter=status_filter,
        tenant_filter=tenant_filter,
    )
    return [AdminHistoryOut.model_validate(r) for r in raw_history]
