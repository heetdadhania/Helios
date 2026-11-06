"""Repository for querying and recording immutable audit events in meta.audit_trail."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.repositories.base import BaseRepository

logger = logging.getLogger("helios.repositories.audit")


class AuditRepository(BaseRepository):
    """Repository handling read and write operations against meta.audit_trail."""

    def __init__(self, cursor: Optional[Cursor] = None, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
        self.audit_table = f"`{self.catalog}`.`meta`.`audit_trail`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"

    def write_audit_log(
        self,
        actor_user_id: Optional[int],
        actor_role: Optional[str],
        action: str,
        tenant_id: Optional[int] = None,
        batch_id: Optional[str] = None,
        reason: Optional[str] = None,
        details_json: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Insert an immutable administrative or operational audit row into meta.audit_trail.
        Safely serializes dictionaries to JSON and catches transient failures to prevent
        breaking primary transaction flows.
        """
        if isinstance(details_json, dict):
            details_str = json.dumps(details_json)
        else:
            details_str = details_json

        query = f"""
            INSERT INTO {self.audit_table} (
                occurred_at, actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json
            )
            VALUES (
                current_timestamp(), :actor_user_id, :actor_role, :action, :tenant_id, :batch_id, :reason, :details_json
            )
        """
        try:
            self.execute_non_query(
                query,
                {
                    "actor_user_id": actor_user_id,
                    "actor_role": actor_role,
                    "action": action,
                    "tenant_id": tenant_id,
                    "batch_id": batch_id,
                    "reason": reason,
                    "details_json": details_str,
                },
            )
        except Exception as exc:
            logger.error("Failed to write to meta.audit_trail [action=%s]: %s", action, exc)

    def list_audit_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        tenant_id: Optional[int] = None,
        organization: Optional[str] = None,
        order_by: str = "a.occurred_at DESC, a.audit_id DESC",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query paginated audit logs with multi-column filtering:
        - Date range: start_date and end_date (inclusive)
        - Actor: User ID or substring on name/email/role
        - Action: Exact match or substring
        - Organization: Tenant ID or substring on business name
        Returns a tuple of (log_records, total_count).
        """
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if start_date:
            where_clauses.append("to_date(a.occurred_at) >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_clauses.append("to_date(a.occurred_at) <= :end_date")
            params["end_date"] = end_date

        if actor:
            actor_clean = str(actor).strip()
            if actor_clean.isdigit():
                where_clauses.append(
                    "(a.actor_user_id = :actor_id OR lower(u.name) LIKE :actor_like OR lower(u.email) LIKE :actor_like)"
                )
                params["actor_id"] = int(actor_clean)
                params["actor_like"] = f"%{actor_clean.lower()}%"
            else:
                where_clauses.append(
                    "(lower(u.name) LIKE :actor_like OR lower(u.email) LIKE :actor_like OR lower(a.actor_role) LIKE :actor_like)"
                )
                params["actor_like"] = f"%{actor_clean.lower()}%"

        if action:
            action_clean = str(action).strip().lower()
            if action_clean != "all" and action_clean != "":
                where_clauses.append(
                    "(lower(a.action) = :action OR lower(a.action) LIKE :action_like)"
                )
                params["action"] = action_clean
                params["action_like"] = f"%{action_clean}%"

        # Resolve organization / tenant_id
        effective_org = tenant_id if tenant_id is not None else organization
        if effective_org is not None:
            org_str = str(effective_org).strip()
            if org_str.isdigit():
                where_clauses.append("a.tenant_id = :tenant_id")
                params["tenant_id"] = int(org_str)
            elif org_str.lower() != "all" and org_str != "":
                where_clauses.append(
                    "(lower(t.business_name) LIKE :org_like OR cast(a.tenant_id as string) = :org_exact)"
                )
                params["org_like"] = f"%{org_str.lower()}%"
                params["org_exact"] = org_str

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count query for pagination
        count_query = f"""
            SELECT count(*) as total
            FROM {self.audit_table} a
            LEFT JOIN {self.users_table} u ON a.actor_user_id = u.user_id
            LEFT JOIN {self.tenants_table} t ON a.tenant_id = t.tenant_id
            {where_sql}
        """
        count_res = self.execute_single(count_query, params)
        total = int(count_res.get("total", 0)) if count_res else 0

        # Items query with offset & limit
        offset = max(0, (page - 1) * page_size)
        query_params = {**params, "limit": page_size, "offset": offset}

        select_query = f"""
            SELECT 
                a.audit_id,
                cast(a.occurred_at as string) as occurred_at,
                a.actor_user_id,
                a.actor_role,
                coalesce(u.name, 'System') as actor_name,
                coalesce(u.email, '') as actor_email,
                a.action,
                a.tenant_id,
                coalesce(t.business_name, '') as tenant_name,
                a.batch_id,
                a.reason,
                a.details_json
            FROM {self.audit_table} a
            LEFT JOIN {self.users_table} u ON a.actor_user_id = u.user_id
            LEFT JOIN {self.tenants_table} t ON a.tenant_id = t.tenant_id
            {where_sql}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """
        items = self.execute_query(select_query, query_params)
        return items, total

