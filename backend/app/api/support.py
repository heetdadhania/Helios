from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.support_repository import SupportRepository
from app.schemas.auth import UserOut
from app.schemas.support import (
    SupportFlagCreate,
    SupportMessageCreate,
    SupportMessageOut,
    SupportMessageResolveResponse,
)
from app.services.support_service import SupportService

router = APIRouter()


@router.post(
    "/flag",
    response_model=SupportMessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Flag for Admin Escalation",
    description=(
        "Submit an issue or pipeline escalation flagged by a Team Member or Admin. "
        "Always routes to an Admin recipient regardless of tenant team assignments, "
        "and tags message_source as 'team_member'."
    ),
)
def flag_for_admin(
    payload: SupportFlagCreate,
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> SupportMessageOut:
    """
    Escalate an issue to Admin with message_source='team_member'.
    """
    repo = SupportRepository(cursor)
    return SupportService.flag_for_admin(
        tenant_id=payload.tenant_id,
        from_user_id=current_user.id,
        message=payload.message,
        batch_id=payload.batch_id,
        repo=repo,
    )


@router.post(
    "/messages",
    response_model=SupportMessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Contact or Update Request",
    description=(
        "Send a message or status inquiry from an SMB Owner to their assigned Team Member "
        "(or fallback to an Admin if unassigned). Creates a record in platform.support_messages "
        "and triggers a notification to the recipient without exposing pipeline internals."
    ),
)
def create_support_message(
    payload: SupportMessageCreate,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> SupportMessageOut:
    """
    Create a routed support inquiry from the authenticated SMB Owner.
    """
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to any tenant organization.",
        )

    repo = SupportRepository(cursor)
    return SupportService.send_message(
        tenant_id=int(current_user.tenant_id),
        from_user_id=current_user.id,
        message=payload.message,
        repo=repo,
    )


@router.get(
    "/messages",
    response_model=List[SupportMessageOut],
    status_code=status.HTTP_200_OK,
    summary="List Support Messages",
    description=(
        "Retrieve support messages. Team Members see only messages routed to them. "
        "Admins see all messages system-wide across all tenants."
    ),
)
def get_support_messages(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter messages by status: open, resolved, all"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[SupportMessageOut]:
    """
    List messages received by the caller (Team Member) or all (Admin).
    """
    repo = SupportRepository(cursor)
    return SupportService.get_messages(
        user_id=current_user.id,
        user_role=current_user.role.value,
        status_filter=status_filter,
        repo=repo,
    )


@router.post(
    "/messages/{message_id}/resolve",
    response_model=SupportMessageResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Support Message as Resolved",
    description="Mark an inquiry as resolved by the assigned Team Member or an Admin.",
)
def resolve_support_message(
    message_id: int,
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> SupportMessageResolveResponse:
    """
    Mark the specified support message as resolved.
    """
    repo = SupportRepository(cursor)
    return SupportService.resolve_message(
        message_id=message_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        repo=repo,
    )
