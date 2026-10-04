import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.pipeline_health")


class PipelineHealthRepository:
    """Repository managing pipeline execution observability, stage tracking, and recovery."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"
        self.pending_table = f"`{self.catalog}`.`platform`.`pending_uploads`"
        self.team_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.audit_table = f"`{self.catalog}`.`meta`.`etl_audit_log`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.notifications_table = f"`{self.catalog}`.`platform`.`notification_log`"

    def _fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Helper to execute query and return list of dictionaries."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def _fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Helper to execute query and return a single dictionary or None."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        row = self.cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return dict(zip(columns, row))

    def check_user_tenant_access(self, user_id: int, user_role: str, tenant_id: int) -> bool:
        """Verify whether the active user has access to data for the given tenant."""
        if user_role.lower() == "admin":
            return True
        if user_role.lower() != "team_member":
            return False

        query = f"SELECT 1 FROM {self.team_table} WHERE user_id = :user_id AND tenant_id = :tenant_id LIMIT 1"
        self.cursor.execute(query, {"user_id": user_id, "tenant_id": tenant_id})
        return self.cursor.fetchone() is not None

    def list_runs(
        self,
        user_id: int,
        user_role: str,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all pipeline runs.
        Admins see all tenants; Team Members see only their assigned tenants.
        """
        is_admin = user_role.lower() == "admin"
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if status_filter:
            norm_filter = status_filter.strip().lower()
            if norm_filter in ("all", "*", ""):
                pass
            elif norm_filter in ("running", "in_progress", "processing"):
                where_clauses.append(
                    "(LOWER(ps.status) LIKE '%running%' OR LOWER(ps.status) IN ('processing', 'in_progress', 'running'))"
                )
            elif norm_filter in ("success", "completed"):
                where_clauses.append("LOWER(ps.status) IN ('success', 'completed')")
            elif norm_filter in ("failed", "failure", "error"):
                where_clauses.append("LOWER(ps.status) IN ('failed', 'failure', 'error')")
            else:
                where_clauses.append("LOWER(ps.status) = :status_filter")
                params["status_filter"] = norm_filter

        if is_admin:
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"""
                SELECT 
                    ps.batch_id,
                    ps.tenant_id,
                    t.business_name AS tenant,
                    t.business_name AS tenant_name,
                    COALESCE(pu.source_type, 'upload') AS source_type,
                    ps.stage AS current_stage,
                    ps.status,
                    ps.created_at AS started_at,
                    ps.updated_at,
                    ps.error_message
                FROM {self.pipeline_table} ps
                LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
                LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
                {where_sql}
                ORDER BY ps.created_at DESC
            """
            return self._fetch_all(query, params if params else None)

        # Team member query with tenant assignment constraint
        where_clauses.append("ta.user_id = :user_id")
        params["user_id"] = user_id
        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                t.business_name AS tenant,
                t.business_name AS tenant_name,
                COALESCE(pu.source_type, 'upload') AS source_type,
                ps.stage AS current_stage,
                ps.status,
                ps.created_at AS started_at,
                ps.updated_at,
                ps.error_message
            FROM {self.pipeline_table} ps
            INNER JOIN {self.team_table} ta ON ps.tenant_id = ta.tenant_id
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
            {where_sql}
            ORDER BY ps.created_at DESC
        """
        return self._fetch_all(query, params)

    def get_run_detail(
        self,
        batch_id: str,
        user_id: int,
        user_role: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch full run details including tenant metadata and linked audit logs."""
        query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                ps.upload_id,
                t.business_name AS tenant,
                t.business_name AS tenant_name,
                COALESCE(pu.source_type, 'upload') AS source_type,
                ps.stage AS current_stage,
                ps.status,
                ps.created_at AS started_at,
                ps.updated_at,
                ps.error_message
            FROM {self.pipeline_table} ps
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            LEFT JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
            WHERE ps.batch_id = :batch_id
            LIMIT 1
        """
        run_record = self._fetch_one(query, {"batch_id": batch_id})
        if not run_record:
            return None

        tenant_id = int(run_record["tenant_id"])
        if not self.check_user_tenant_access(user_id, user_role, tenant_id):
            return None

        audit_query = f"""
            SELECT 
                log_id,
                batch_id,
                stage,
                row_count,
                status,
                started_at,
                completed_at,
                error_message
            FROM {self.audit_table}
            WHERE batch_id = :batch_id
            ORDER BY started_at ASC, log_id ASC
        """
        audit_rows = self._fetch_all(audit_query, {"batch_id": batch_id})
        run_record["audit_logs"] = audit_rows
        return run_record

    def update_status_for_retry(
        self,
        batch_id: str,
        stage: str,
        status: str,
        clear_error: bool = True,
    ) -> None:
        """Update batch status and stage when re-running from a failed stage."""
        err_sql = "error_message = NULL," if clear_error else ""
        query = f"""
            UPDATE {self.pipeline_table}
            SET stage = :stage,
                status = :status,
                {err_sql}
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
        """
        self.cursor.execute(query, {"batch_id": batch_id, "stage": stage, "status": status})

    def mark_restart_required(self, batch_id: str, message: str) -> Optional[Dict[str, Any]]:
        """Mark batch as 'restart_required' and update pending uploads if present."""
        query_tenant = f"SELECT tenant_id, upload_id FROM {self.pipeline_table} WHERE batch_id = :batch_id LIMIT 1"
        info = self._fetch_one(query_tenant, {"batch_id": batch_id})
        if not info:
            return None

        update_ps = f"""
            UPDATE {self.pipeline_table}
            SET status = 'restart_required',
                error_message = :message,
                updated_at = current_timestamp()
            WHERE batch_id = :batch_id
        """
        self.cursor.execute(update_ps, {"batch_id": batch_id, "message": message})

        if info.get("upload_id") is not None:
            update_upload = f"""
                UPDATE {self.pending_table}
                SET status = 'restart_required'
                WHERE upload_id = :upload_id
            """
            try:
                self.cursor.execute(update_upload, {"upload_id": info["upload_id"]})
            except Exception as exc:
                logger.warning("Could not update pending_uploads for restart: %s", exc)

        return info

    def notify_smb_owner(self, tenant_id: int, message: str) -> None:
        """Send warning notification to tenant's SMB Owner requesting re-upload."""
        owner_query = f"""
            SELECT user_id FROM {self.users_table}
            WHERE tenant_id = :tenant_id AND role = 'smb_owner' AND is_active = true
            LIMIT 1
        """
        owner = self._fetch_one(owner_query, {"tenant_id": tenant_id})
        target_user_id = owner["user_id"] if owner else None

        insert_notify = f"""
            INSERT INTO {self.notifications_table} (
                tenant_id, user_id, message, type, is_read, created_at
            )
            VALUES (
                :tenant_id, :user_id, :message, 'warning', false, current_timestamp()
            )
        """
        self.cursor.execute(
            insert_notify,
            {"tenant_id": tenant_id, "user_id": target_user_id, "message": message},
        )
