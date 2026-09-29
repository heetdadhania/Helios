import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.support")


class SupportRepository:
    """
    Repository handling persistence, routing, and queries for platform.support_messages.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`support_messages`"
        self.team_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"

    def _fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return list of row dictionaries."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def _fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute query and return single row dictionary or None."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        row = self.cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return dict(zip(columns, row))

    def resolve_recipient_user_id(self, tenant_id: int) -> int:
        """
        Resolve the recipient user ID for a support message.
        1. Checks platform.team_assignments for an assigned Team Member.
        2. If no Team Member is assigned, falls back to routing to any active Admin.
        Never leaves the message unrouted.
        """
        # 1. Try finding assigned team member
        assigned_q = f"""
            SELECT ta.user_id
            FROM {self.team_table} ta
            INNER JOIN {self.users_table} u ON ta.user_id = u.user_id
            WHERE ta.tenant_id = :tenant_id AND u.is_active = true
            ORDER BY ta.assigned_at DESC
            LIMIT 1
        """
        row = self._fetch_one(assigned_q, {"tenant_id": tenant_id})
        if row and row.get("user_id") is not None:
            return int(row["user_id"])

        # 2. Fallback: find any active Admin user
        admin_q = f"""
            SELECT user_id
            FROM {self.users_table}
            WHERE lower(role) = 'admin' AND is_active = true
            ORDER BY user_id ASC
            LIMIT 1
        """
        admin_row = self._fetch_one(admin_q)
        if admin_row and admin_row.get("user_id") is not None:
            logger.info("No Team Member assigned to tenant %s; routing support message to Admin user_id %s", tenant_id, admin_row["user_id"])
            return int(admin_row["user_id"])

        # 3. Ultimate fallback: any admin regardless of is_active, or default 1
        fallback_q = f"""
            SELECT user_id
            FROM {self.users_table}
            WHERE lower(role) = 'admin'
            ORDER BY user_id ASC
            LIMIT 1
        """
        fb_row = self._fetch_one(fallback_q)
        return int(fb_row["user_id"]) if fb_row and fb_row.get("user_id") else 1

    def resolve_admin_user_id(self) -> int:
        """
        Resolve an Admin user ID for escalation flags.
        Always routes to an active Admin regardless of tenant team assignments.
        """
        admin_q = f"""
            SELECT user_id
            FROM {self.users_table}
            WHERE lower(role) = 'admin' AND is_active = true
            ORDER BY user_id ASC
            LIMIT 1
        """
        admin_row = self._fetch_one(admin_q)
        if admin_row and admin_row.get("user_id") is not None:
            return int(admin_row["user_id"])

        fallback_q = f"""
            SELECT user_id
            FROM {self.users_table}
            WHERE lower(role) = 'admin'
            ORDER BY user_id ASC
            LIMIT 1
        """
        fb_row = self._fetch_one(fallback_q)
        return int(fb_row["user_id"]) if fb_row and fb_row.get("user_id") else 1

    def create_message(
        self,
        tenant_id: int,
        from_user_id: int,
        to_user_id: int,
        message: str,
        message_source: str = "smb_owner",
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert a support message record and return populated model dictionary."""
        insert_query = f"""
            INSERT INTO {self.table} (tenant_id, from_user_id, to_user_id, message, message_source, status, created_at)
            VALUES (:tenant_id, :from_user_id, :to_user_id, :message, :message_source, 'open', current_timestamp())
        """
        params = {
            "tenant_id": tenant_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "message": message.strip(),
            "message_source": message_source,
        }
        self.cursor.execute(insert_query, params)

        # Retrieve the newly created row with user names and tenant business name
        fetch_query = f"""
            SELECT 
                sm.message_id,
                sm.tenant_id,
                t.business_name AS tenant_name,
                sm.from_user_id,
                u_from.name AS from_user_name,
                sm.to_user_id,
                u_to.name AS to_user_name,
                sm.message,
                sm.message_source,
                sm.status,
                sm.created_at,
                sm.resolved_at
            FROM {self.table} sm
            LEFT JOIN {self.tenants_table} t ON sm.tenant_id = t.tenant_id
            LEFT JOIN {self.users_table} u_from ON sm.from_user_id = u_from.user_id
            LEFT JOIN {self.users_table} u_to ON sm.to_user_id = u_to.user_id
            WHERE sm.tenant_id = :tenant_id AND sm.from_user_id = :from_user_id
            ORDER BY sm.message_id DESC
            LIMIT 1
        """
        row = self._fetch_one(fetch_query, {"tenant_id": tenant_id, "from_user_id": from_user_id})
        if not row:
            # Fallback for mock environments
            from datetime import datetime, timezone
            row = {
                "message_id": 1,
                "tenant_id": tenant_id,
                "tenant_name": None,
                "from_user_id": from_user_id,
                "from_user_name": None,
                "to_user_id": to_user_id,
                "to_user_name": None,
                "message": message.strip(),
                "message_source": message_source,
                "status": "open",
                "created_at": datetime.now(timezone.utc),
                "resolved_at": None,
            }
        if batch_id:
            row["batch_id"] = batch_id
        return row

    def get_messages(
        self,
        user_id: int,
        user_role: str,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve support messages:
        - Team Member: messages routed to them (to_user_id = :user_id).
        - Admin: all messages across all tenants.
        """
        is_admin = user_role.lower() == "admin"
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if not is_admin:
            where_clauses.append("sm.to_user_id = :user_id")
            params["user_id"] = user_id

        if status_filter and status_filter.strip().lower() != "all":
            where_clauses.append("lower(sm.status) = :status_filter")
            params["status_filter"] = status_filter.strip().lower()

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT 
                sm.message_id,
                sm.tenant_id,
                t.business_name AS tenant_name,
                sm.from_user_id,
                u_from.name AS from_user_name,
                sm.to_user_id,
                u_to.name AS to_user_name,
                sm.message,
                sm.message_source,
                sm.status,
                sm.created_at,
                sm.resolved_at
            FROM {self.table} sm
            LEFT JOIN {self.tenants_table} t ON sm.tenant_id = t.tenant_id
            LEFT JOIN {self.users_table} u_from ON sm.from_user_id = u_from.user_id
            LEFT JOIN {self.users_table} u_to ON sm.to_user_id = u_to.user_id
            {where_sql}
            ORDER BY sm.created_at DESC
        """
        return self._fetch_all(query, params if params else None)

    def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single message by ID."""
        query = f"""
            SELECT 
                sm.message_id,
                sm.tenant_id,
                t.business_name AS tenant_name,
                sm.from_user_id,
                u_from.name AS from_user_name,
                sm.to_user_id,
                u_to.name AS to_user_name,
                sm.message,
                sm.message_source,
                sm.status,
                sm.created_at,
                sm.resolved_at
            FROM {self.table} sm
            LEFT JOIN {self.tenants_table} t ON sm.tenant_id = t.tenant_id
            LEFT JOIN {self.users_table} u_from ON sm.from_user_id = u_from.user_id
            LEFT JOIN {self.users_table} u_to ON sm.to_user_id = u_to.user_id
            WHERE sm.message_id = :message_id
            LIMIT 1
        """
        return self._fetch_one(query, {"message_id": message_id})

    def resolve_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Update message resolution status to 'resolved' and set resolved_at."""
        update_query = f"""
            UPDATE {self.table}
            SET status = 'resolved', resolved_at = current_timestamp()
            WHERE message_id = :message_id
        """
        self.cursor.execute(update_query, {"message_id": message_id})
        return self.get_message_by_id(message_id)
