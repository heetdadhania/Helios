import logging
from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Connection, Cursor
except ImportError:
    Cursor = Any  # type: ignore
    Connection = Any  # type: ignore

from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.notification_repository import NotificationRepository
from app.schemas.auth import UserOut
from app.schemas.notification import (
    NotificationOut,
    NotificationReadResponse,
    NotificationType,
)

logger = logging.getLogger("helios.services.notification")


def _acquire_cursor(cursor: Optional[Cursor] = None) -> tuple[Cursor, Optional[Connection]]:
    """Acquires active cursor or opens a connection."""
    if cursor is not None:
        return cursor, None
    try:
        from app.db.base import get_databricks_connection
        conn = get_databricks_connection()
        return conn.cursor(), conn
    except Exception as exc:
        logger.warning("Could not establish direct database connection for notifications: %s", exc)
        return None, None  # type: ignore


class NotificationService:
    """Service handling multi-tenant notification dispatch and lifecycle."""

    @classmethod
    def notify_upload_received(
        cls,
        tenant_id: int,
        batch_id: str,
        user_id: Optional[int] = None,
        source_type: str = "upload",
        cursor: Optional[Cursor] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Triggered when upload, DB sync, or API push is received.
        Notifies SMB Owner: 'Your data is being processed'.
        """
        message = "Your data is being processed"
        logger.info(
            "Dispatching upload_received notification for tenant %d, batch %s (%s)",
            tenant_id,
            batch_id,
            source_type,
        )

        active_cursor, owned_conn = _acquire_cursor(cursor)
        if active_cursor is None:
            return None

        try:
            repo = NotificationRepository(active_cursor)
            return repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                message=message,
                type=NotificationType.INFO.value,
            )
        except Exception as exc:
            logger.error("Failed to persist upload_received notification for batch %s: %s", batch_id, exc)
            return None
        finally:
            if owned_conn is not None:
                try:
                    active_cursor.close()
                    owned_conn.close()
                except Exception:
                    pass

    @classmethod
    def notify_pipeline_failed(
        cls,
        tenant_id: int,
        batch_id: str,
        stage: str,
        error_message: Optional[str] = None,
        cursor: Optional[Cursor] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Triggered when an ETL pipeline stage fails.
        Notifies assigned Team Member(s) and Admin:
        'Pipeline failure at stage '{stage}' for batch '{batch_id}'. Error: {error_message}'
        """
        err_snippet = f": {error_message}" if error_message else ""
        message = f"Pipeline failure at stage '{stage}' for batch '{batch_id}'{err_snippet}"
        logger.warning(
            "Dispatching pipeline_failed notification for tenant %d, batch %s, stage %s",
            tenant_id,
            batch_id,
            stage,
        )

        active_cursor, owned_conn = _acquire_cursor(cursor)
        if active_cursor is None:
            return None

        try:
            repo = NotificationRepository(active_cursor)
            # Log failure notification scoped to the tenant (visible to assigned Team Members and Admins)
            return repo.create(
                tenant_id=tenant_id,
                user_id=None,
                message=message,
                type=NotificationType.ERROR.value,
            )
        except Exception as exc:
            logger.error("Failed to persist pipeline_failed notification for batch %s: %s", batch_id, exc)
            return None
        finally:
            if owned_conn is not None:
                try:
                    active_cursor.close()
                    owned_conn.close()
                except Exception:
                    pass

    @classmethod
    def notify_dashboard_ready(
        cls,
        tenant_id: int,
        batch_id: str,
        user_id: Optional[int] = None,
        cursor: Optional[Cursor] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Triggered when Gold dimensional transformations complete successfully.
        Notifies SMB Owner: 'Your dashboard is ready to view'.
        """
        message = "Your dashboard is ready to view"
        logger.info(
            "Dispatching dashboard_ready notification for tenant %d, batch %s",
            tenant_id,
            batch_id,
        )

        active_cursor, owned_conn = _acquire_cursor(cursor)
        if active_cursor is None:
            return None

        try:
            repo = NotificationRepository(active_cursor)
            return repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                message=message,
                type=NotificationType.PIPELINE_SUCCESS.value,
            )
        except Exception as exc:
            logger.error("Failed to persist dashboard_ready notification for batch %s: %s", batch_id, exc)
            return None
        finally:
            if owned_conn is not None:
                try:
                    active_cursor.close()
                    owned_conn.close()
                except Exception:
                    pass

    @classmethod
    def notify_restart_required(
        cls,
        tenant_id: int,
        batch_id: str,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
        cursor: Optional[Cursor] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Triggered during Module 12's Full Restart flow by Team Member/Admin.
        Notifies SMB Owner: 'Please re-upload your data — we need a fresh copy to continue processing'.
        """
        message = "Please re-upload your data — we need a fresh copy to continue processing"
        logger.info(
            "Dispatching restart_required notification for tenant %d, batch %s",
            tenant_id,
            batch_id,
        )

        active_cursor, owned_conn = _acquire_cursor(cursor)
        if active_cursor is None:
            return None

        try:
            repo = NotificationRepository(active_cursor)
            return repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                message=message,
                type=NotificationType.WARNING.value,
            )
        except Exception as exc:
            logger.error("Failed to persist restart_required notification for batch %s: %s", batch_id, exc)
            return None
        finally:
            if owned_conn is not None:
                try:
                    active_cursor.close()
                    owned_conn.close()
                except Exception:
                    pass

    @classmethod
    def get_user_notifications(
        cls,
        current_user: UserOut,
        repo: NotificationRepository,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NotificationOut]:
        """Fetch notifications scoped to the current user's role and tenant."""
        raw_items = repo.list_for_user(
            user_id=current_user.id,
            user_role=current_user.role.value,
            tenant_id=current_user.tenant_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        results: List[NotificationOut] = []
        for r in raw_items:
            results.append(
                NotificationOut(
                    notification_id=int(r["notification_id"]),
                    tenant_id=int(r["tenant_id"]) if r.get("tenant_id") is not None else None,
                    user_id=int(r["user_id"]) if r.get("user_id") is not None else None,
                    message=str(r["message"]),
                    type=str(r.get("type") or "info"),
                    is_read=bool(r.get("is_read", False)),
                    created_at=r.get("created_at"),
                )
            )
        return results

    @classmethod
    def mark_notification_as_read(
        cls,
        notification_id: int,
        current_user: UserOut,
        repo: NotificationRepository,
    ) -> NotificationReadResponse:
        """Mark a notification as read with boundary check."""
        success = repo.mark_as_read(
            notification_id=notification_id,
            user_id=current_user.id,
            user_role=current_user.role.value,
            tenant_id=current_user.tenant_id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification {notification_id} not found or access denied.",
            )
        return NotificationReadResponse(
            notification_id=notification_id,
            is_read=True,
            message="Notification marked as read.",
        )
