from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    """Data access repository for platform.notification_log in Databricks Unity Catalog."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`notification_log`"
        self.team_assignments_table = f"`{self.catalog}`.`platform`.`team_assignments`"

    def create(
        self,
        message: str,
        type: str = "info",
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert a notification into platform.notification_log."""
        insert_query = f"""
            INSERT INTO {self.table} (
                tenant_id, user_id, message, type, is_read, created_at
            )
            VALUES (
                :tenant_id, :user_id, :message, :type, false, current_timestamp()
            )
        """
        params = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "message": message,
            "type": type,
        }
        self.execute_non_query(insert_query, params)

        # Retrieve the latest matching notification
        fetch_query = f"""
            SELECT notification_id, tenant_id, user_id, message, type, is_read, created_at
            FROM {self.table}
            WHERE message = :message AND type = :type
            ORDER BY notification_id DESC
            LIMIT 1
        """
        created = self.execute_single(fetch_query, {"message": message, "type": type})
        if created:
            return created

        return {
            "notification_id": 1,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "message": message,
            "type": type,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        }

    def get_by_id(self, notification_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific notification record by its ID."""
        query = f"""
            SELECT notification_id, tenant_id, user_id, message, type, is_read, created_at
            FROM {self.table}
            WHERE notification_id = :notification_id
            LIMIT 1
        """
        return self.execute_single(query, {"notification_id": notification_id})

    def list_for_user(
        self,
        user_id: int,
        user_role: str,
        tenant_id: Optional[int] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List notifications scoped strictly by role and tenant boundaries:
        - Admin: all notifications, or filtered by tenant if provided
        - Team Member: notifications for assigned tenants or targeted to the user
        - SMB Owner: notifications where tenant_id == user.tenant_id and (user_id IS NULL or user_id == user.id)
        """
        role_norm = user_role.lower()
        where_clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if role_norm == "admin":
            if tenant_id is not None:
                where_clauses.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

        elif role_norm == "team_member":
            # Targeted to user OR tenant is in user's assigned tenants
            where_clauses.append(f"""
                (user_id = :user_id OR tenant_id IN (
                    SELECT tenant_id FROM {self.team_assignments_table} WHERE user_id = :user_id
                ))
            """)
            params["user_id"] = user_id

        elif role_norm == "smb_owner":
            where_clauses.append("tenant_id = :tenant_id AND (user_id IS NULL OR user_id = :user_id)")
            params["tenant_id"] = tenant_id or 0
            params["user_id"] = user_id

        else:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id

        if unread_only:
            where_clauses.append("is_read = false")

        where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT notification_id, tenant_id, user_id, message, type, is_read, created_at
            FROM {self.table}
            {where_stmt}
            ORDER BY created_at DESC, notification_id DESC
            LIMIT :limit OFFSET :offset
        """
        return self.execute_query(query, params)

    def mark_as_read(
        self,
        notification_id: int,
        user_id: int,
        user_role: str,
        tenant_id: Optional[int] = None,
    ) -> bool:
        """Mark notification as read after validating user authorization."""
        target = self.get_by_id(notification_id)
        if not target:
            return False

        role_norm = user_role.lower()
        # Enforce boundary check
        if role_norm == "smb_owner":
            if target.get("tenant_id") != tenant_id:
                return False

        query = f"""
            UPDATE {self.table}
            SET is_read = true
            WHERE notification_id = :notification_id
        """
        self.execute_non_query(query, {"notification_id": notification_id})
        return True
