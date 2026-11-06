from typing import Any, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.notification_repository import NotificationRepository
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationOut, NotificationReadResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NotificationOut],
    status_code=status.HTTP_200_OK,
    summary="List User Notifications",
    description="Retrieve operational notifications scoped by role and tenant boundaries with server-side pagination.",
)
def list_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    limit: Optional[int] = Query(default=None, description="Legacy limit"),
    offset: Optional[int] = Query(default=None, description="Legacy offset"),
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[NotificationOut]:
    """List operational and pipeline event notifications for the authenticated user with server-side pagination."""
    repo = NotificationRepository(cursor)
    return NotificationService.get_user_notifications(
        current_user=current_user,
        repo=repo,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{id}/read",
    response_model=NotificationReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification Read",
    description="Mark a specific notification as read, enforcing tenant boundaries.",
)
def mark_as_read(
    id: int,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> NotificationReadResponse:
    """Mark notification read status."""
    repo = NotificationRepository(cursor)
    return NotificationService.mark_notification_as_read(
        notification_id=id,
        current_user=current_user,
        repo=repo,
    )
