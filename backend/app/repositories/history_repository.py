import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.history")


class HistoryRepository:
    """
    Repository providing role-specific views into pipeline execution history,
    pending uploads, and ETL audit logs.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.pending_table = f"`{self.catalog}`.`platform`.`pending_uploads`"
        self.audit_table = f"`{self.catalog}`.`meta`.`etl_audit_log`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.team_table = f"`{self.catalog}`.`platform`.`team_assignments`"

    def _fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Helper executing a query and returning list of dictionaries."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def _map_smb_status(status_raw: Optional[str], stage_raw: Optional[str] = None) -> str:
        """
        Map operational status and stage to a simplified, customer-friendly status string:
        - 'Ready': ETL pipeline finished successfully.
        - 'Needs attention — please resend': Ingestion or processing failed.
        - 'Processing': Data received, awaiting review, or currently running through Medallion stages.
        """
        s = (status_raw or "").strip().lower()
        if s in ("success", "completed", "ready"):
            return "Ready"
        elif s in ("failed", "rejected", "error"):
            return "Needs attention — please resend"
        return "Processing"

    @staticmethod
    def _format_date(val: Any) -> str:
        """Format timestamp into a clean date-time string."""
        if val is None:
            return ""
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d %H:%M:%S")
        return str(val)

    def get_smb_history(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Fetch submission history strictly scoped to the authenticated tenant.
        Returns customer-facing plain-language status without technical stage/error jargon.
        """
        query = f"""
            SELECT 
                ps.batch_id,
                ps.status,
                ps.stage,
                ps.created_at
            FROM {self.pipeline_table} ps
            WHERE ps.tenant_id = :tenant_id
            ORDER BY ps.created_at DESC
        """
        raw_rows = self._fetch_all(query, {"tenant_id": tenant_id})

        results = []
        for r in raw_rows:
            results.append(
                {
                    "batch_id": str(r["batch_id"]),
                    "date": self._format_date(r.get("created_at")),
                    "status": self._map_smb_status(r.get("status"), r.get("stage")),
                    "label": "Data received",
                }
            )
        return results

    def get_team_history(
        self,
        user_id: int,
        user_role: str,
        status_filter: Optional[str] = None,
        tenant_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch operational submission history.
        - Team Member: strictly scoped to assigned tenants.
        - Admin: all tenants.
        Supports filtering by status and tenant business name or ID.
        """
        is_admin = user_role.lower() == "admin"
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if not is_admin:
            where_clauses.append(
                f"ps.tenant_id IN (SELECT tenant_id FROM {self.team_table} WHERE user_id = :user_id)"
            )
            params["user_id"] = user_id

        if status_filter:
            where_clauses.append("lower(ps.status) = :status_filter")
            params["status_filter"] = status_filter.strip().lower()

        if tenant_filter:
            clean_tf = tenant_filter.strip().lower()
            if clean_tf.isdigit():
                where_clauses.append("(ps.tenant_id = :tenant_num OR lower(t.business_name) LIKE :tenant_like)")
                params["tenant_num"] = int(clean_tf)
                params["tenant_like"] = f"%{clean_tf}%"
            else:
                where_clauses.append("lower(t.business_name) LIKE :tenant_like")
                params["tenant_like"] = f"%{clean_tf}%"

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                COALESCE(t.business_name, concat('Tenant #', cast(ps.tenant_id AS STRING))) AS tenant,
                COALESCE(pu.source_type, 'upload') AS source_type,
                ps.stage,
                ps.status,
                COALESCE(ps.error_message, al.error_message) AS error_message,
                ps.created_at AS timestamp
            FROM {self.pipeline_table} ps
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
            LEFT JOIN (
                SELECT batch_id, max(error_message) AS error_message
                FROM {self.audit_table}
                WHERE error_message IS NOT NULL AND trim(error_message) != ''
                GROUP BY batch_id
            ) al ON ps.batch_id = al.batch_id
            {where_sql}
            ORDER BY ps.created_at DESC
        """
        return self._fetch_all(query, params if params else None)

    def get_admin_history(
        self,
        status_filter: Optional[str] = None,
        tenant_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch system-wide submission history including the handling Team Member identity.
        Never scoped to tenant assignments.
        Surfaces 'handled_by': Team Member name if handled by Team Member, or 'N/A' if Admin / automated.
        """
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if status_filter:
            where_clauses.append("lower(ps.status) = :status_filter")
            params["status_filter"] = status_filter.strip().lower()

        if tenant_filter:
            clean_tf = tenant_filter.strip().lower()
            if clean_tf.isdigit():
                where_clauses.append("(ps.tenant_id = :tenant_num OR lower(t.business_name) LIKE :tenant_like)")
                params["tenant_num"] = int(clean_tf)
                params["tenant_like"] = f"%{clean_tf}%"
            else:
                where_clauses.append("lower(t.business_name) LIKE :tenant_like")
                params["tenant_like"] = f"%{clean_tf}%"

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                COALESCE(t.business_name, concat('Tenant #', cast(ps.tenant_id AS STRING))) AS tenant,
                COALESCE(pu.source_type, 'upload') AS source_type,
                ps.stage,
                ps.status,
                COALESCE(ps.error_message, al.error_message) AS error_message,
                ps.created_at AS timestamp,
                CASE 
                    WHEN lower(u.role) = 'team_member' THEN COALESCE(u.name, 'Team Member')
                    ELSE 'N/A'
                END AS handled_by
            FROM {self.pipeline_table} ps
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
            LEFT JOIN {self.users_table} u ON pu.uploaded_by = u.user_id
            LEFT JOIN (
                SELECT batch_id, max(error_message) AS error_message
                FROM {self.audit_table}
                WHERE error_message IS NOT NULL AND trim(error_message) != ''
                GROUP BY batch_id
            ) al ON ps.batch_id = al.batch_id
            {where_sql}
            ORDER BY ps.created_at DESC
        """
        return self._fetch_all(query, params if params else None)
