from typing import Any, List
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.notification_repository import NotificationRepository
from app.schemas.auth import UserOut
from app.schemas.notification import NotificationOut, NotificationReadResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "",
    response_model=List[NotificationOut],
    status_code=status.HTTP_200_OK,
    summary="List User Notifications",
    description="Retrieve operational notifications scoped by role and tenant boundaries.",
)
def list_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    limit: int = Query(default=50, ge=1, le=100, description="Max notifications to retrieve"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[NotificationOut]:
    """List operational and pipeline event notifications for the authenticated user."""
    repo = NotificationRepository(cursor)
    return NotificationService.get_user_notifications(
        current_user=current_user,
        repo=repo,
        unread_only=unread_only,
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
