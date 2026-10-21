import logging
from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TeamRepository(BaseRepository):
    """
    Data access repository for internal team members and assignments in platform.users
    and platform.team_assignments.
    """

    def __init__(self, cursor: Optional[Cursor] = None, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"
        self.team_assignments_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.support_table = f"`{self.catalog}`.`platform`.`support_messages`"
        self.summary_table = f"`{self.catalog}`.`gold`.`fact_orders_daily_summary`"
        self.dim_date_table = f"`{self.catalog}`.`gold`.`dim_date`"

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str,
        phone_number: str,
        staff_id: Optional[str] = None,
        designation: Optional[str] = None,
        must_change_password: bool = True,
    ) -> Dict[str, Any]:
        """Insert a new team member or admin into platform.users."""
        clean_email = email.strip().lower()
        query = f"""
            INSERT INTO {self.users_table} (
                name,
                email,
                password_hash,
                role,
                phone_number,
                staff_id,
                designation,
                must_change_password,
                is_active,
                created_at
            ) VALUES (
                :name,
                :email,
                :password_hash,
                :role,
                :phone_number,
                :staff_id,
                :designation,
                :must_change_password,
                true,
                current_timestamp()
            )
        """
        self.execute_non_query(
            query,
            {
                "name": name.strip(),
                "email": clean_email,
                "password_hash": password_hash,
                "role": role,
                "phone_number": phone_number.strip(),
                "staff_id": staff_id.strip() if staff_id else None,
                "designation": designation.strip() if designation else None,
                "must_change_password": must_change_password,
            },
        )
        created = self.get_by_email(clean_email)
        if not created:
            raise RuntimeError(f"Team member creation failed for {clean_email}")
        return created

    USER_COLUMNS = """
        user_id,
        tenant_id,
        name,
        email,
        password_hash,
        role,
        coalesce(is_active, true) as is_active,
        created_at,
        phone_number,
        staff_id,
        designation,
        coalesce(must_change_password, false) as must_change_password,
        last_login_at,
        coalesce(failed_login_count, 0) as failed_login_count,
        locked_until,
        password_changed_at
    """

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user by unique email address."""
        query = f"SELECT {self.USER_COLUMNS} FROM {self.users_table} WHERE lower(email) = :email LIMIT 1"
        return self.execute_single(query, {"email": email.strip().lower()})

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch team member by ID along with assigned tenant IDs."""
        query = f"SELECT {self.USER_COLUMNS} FROM {self.users_table} WHERE user_id = :user_id LIMIT 1"
        user = self.execute_single(query, {"user_id": user_id})
        if not user:
            return None
        assigned = self.get_assigned_tenant_ids(user_id)
        user["tenant_ids"] = assigned
        user["assigned_tenants"] = assigned
        if user.get("must_change_password") is None:
            user["must_change_password"] = False
        if user.get("is_active") is None:
            user["is_active"] = True
        if user.get("failed_login_count") is None:
            user["failed_login_count"] = 0
        return user

    def get_assigned_tenant_ids(self, user_id: int) -> List[int]:
        """Fetch all assigned tenant IDs for a given user."""
        query = f"""
            SELECT tenant_id FROM {self.team_assignments_table}
            WHERE user_id = :user_id
            ORDER BY tenant_id ASC
        """
        rows = self.execute_query(query, {"user_id": user_id})
        return [int(r["tenant_id"]) for r in rows if r.get("tenant_id") is not None]

    def list_team_members(self) -> List[Dict[str, Any]]:
        """List all team members and admins, including their assigned tenant IDs."""
        users_query = f"""
            SELECT {self.USER_COLUMNS} FROM {self.users_table}
            WHERE role IN ('team_member', 'admin')
            ORDER BY user_id DESC
        """
        users = self.execute_query(users_query)
        if not users:
            return []

        assignments_query = f"""
            SELECT user_id, tenant_id FROM {self.team_assignments_table}
            ORDER BY user_id, tenant_id ASC
        """
        assignment_rows = self.execute_query(assignments_query)

        user_tenants_map: Dict[int, List[int]] = {}
        for row in assignment_rows:
            u_id = int(row["user_id"])
            t_id = int(row["tenant_id"])
            user_tenants_map.setdefault(u_id, []).append(t_id)

        for user in users:
            u_id = int(user["user_id"])
            assigned = user_tenants_map.get(u_id, [])
            user["tenant_ids"] = assigned
            user["assigned_tenants"] = assigned
            if user.get("must_change_password") is None:
                user["must_change_password"] = False
            if user.get("is_active") is None:
                user["is_active"] = True
            if user.get("failed_login_count") is None:
                user["failed_login_count"] = 0

        return users

    def add_assignments(self, user_id: int, tenant_ids: List[int]) -> None:
        """Insert team assignments for a user. Skips duplicates."""
        existing = set(self.get_assigned_tenant_ids(user_id))
        for tid in tenant_ids:
            if tid not in existing:
                query = f"""
                    INSERT INTO {self.team_assignments_table} (user_id, tenant_id, assigned_at)
                    VALUES (:user_id, :tenant_id, current_timestamp())
                """
                self.execute_non_query(query, {"user_id": user_id, "tenant_id": tid})
                existing.add(tid)

    def replace_assignments(self, user_id: int, tenant_ids: List[int]) -> None:
        """Replace all team assignments for a user with the provided tenant IDs."""
        delete_query = f"DELETE FROM {self.team_assignments_table} WHERE user_id = :user_id"
        self.execute_non_query(delete_query, {"user_id": user_id})
        self.add_assignments(user_id, tenant_ids)

    def set_active_status(self, user_id: int, is_active: bool) -> None:
        """Update is_active status of a user."""
        query = f"UPDATE {self.users_table} SET is_active = :is_active WHERE user_id = :user_id"
        self.execute_non_query(query, {"user_id": user_id, "is_active": is_active})

    def verify_tenants_exist(self, tenant_ids: List[int]) -> List[int]:
        """
        Verify that all tenant IDs exist in platform.tenants.
        Returns list of missing tenant IDs (empty if all exist).
        """
        if not tenant_ids:
            return []
        unique_ids = list(set(tenant_ids))
        id_str = ",".join(str(i) for i in unique_ids)
        query = f"SELECT tenant_id FROM {self.tenants_table} WHERE tenant_id IN ({id_str})"
        rows = self.execute_query(query)
        found_ids = {int(r["tenant_id"]) for r in rows if r.get("tenant_id") is not None}
        missing = [tid for tid in unique_ids if tid not in found_ids]
        return missing

    def get_team_home_data(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieve team member home page data strictly scoped to assigned organizations:
        - assigned organizations with their last data date
        - counts of items pending review, running, failed, and stalled
        - open support messages
        - recent activity
        """
        # 1. Assigned organizations with last data date
        orgs_query = f"""
            SELECT 
                t.tenant_id,
                t.business_name,
                max(d.full_date) AS gold_max_date,
                cast(max(ps.created_at) AS date) AS ps_max_date
            FROM {self.team_assignments_table} ta
            INNER JOIN {self.tenants_table} t ON ta.tenant_id = t.tenant_id
            LEFT JOIN {self.summary_table} s ON t.tenant_id = s.tenant_id
            LEFT JOIN {self.dim_date_table} d ON s.date_id = d.date_id
            LEFT JOIN {self.pipeline_table} ps ON t.tenant_id = ps.tenant_id
            WHERE ta.user_id = :user_id
            GROUP BY t.tenant_id, t.business_name
            ORDER BY t.business_name ASC
        """
        org_rows = self.execute_query(orgs_query, {"user_id": user_id})
        assigned_orgs = []
        for r in org_rows:
            last_date = r.get("gold_max_date") or r.get("ps_max_date")
            assigned_orgs.append({
                "tenant_id": int(r["tenant_id"]),
                "business_name": r["business_name"],
                "last_data_date": str(last_date) if last_date else None,
            })

        # 2. Pipeline counts across assigned orgs
        counts_query = f"""
            SELECT
                COUNT(CASE WHEN LOWER(ps.status) IN ('pending_review', 'awaiting_confirmation') THEN 1 END) AS pending_review_count,
                COUNT(CASE 
                    WHEN LOWER(ps.status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
                         AND (
                             (ps.last_heartbeat_at IS NULL AND ps.created_at >= (current_timestamp() - INTERVAL 15 MINUTES))
                             OR
                             (ps.last_heartbeat_at IS NOT NULL AND ps.last_heartbeat_at >= (current_timestamp() - INTERVAL 15 MINUTES))
                         ) THEN 1 
                END) AS running_count,
                COUNT(CASE WHEN LOWER(ps.status) IN ('failed', 'failure', 'error') THEN 1 END) AS failed_count,
                COUNT(CASE 
                    WHEN LOWER(ps.status) = 'stalled'
                         OR (
                             LOWER(ps.status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
                             AND (
                                 (ps.last_heartbeat_at IS NULL AND ps.created_at < (current_timestamp() - INTERVAL 15 MINUTES))
                                 OR
                                 (ps.last_heartbeat_at IS NOT NULL AND ps.last_heartbeat_at < (current_timestamp() - INTERVAL 15 MINUTES))
                             )
                         ) THEN 1 
                END) AS stalled_count
            FROM {self.pipeline_table} ps
            INNER JOIN {self.team_assignments_table} ta ON ps.tenant_id = ta.tenant_id
            WHERE ta.user_id = :user_id
        """
        count_row = self.execute_single(counts_query, {"user_id": user_id}) or {}
        pipeline_counts = {
            "pending_review": int(count_row.get("pending_review_count") or 0),
            "running": int(count_row.get("running_count") or 0),
            "failed": int(count_row.get("failed_count") or 0),
            "stalled": int(count_row.get("stalled_count") or 0),
        }

        # 3. Open support messages for assigned orgs
        messages_query = f"""
            SELECT 
                sm.message_id,
                sm.tenant_id,
                t.business_name AS tenant_name,
                sm.from_user_id,
                u.name AS from_user_name,
                sm.message,
                sm.created_at
            FROM {self.support_table} sm
            INNER JOIN {self.team_assignments_table} ta ON sm.tenant_id = ta.tenant_id
            LEFT JOIN {self.tenants_table} t ON sm.tenant_id = t.tenant_id
            LEFT JOIN {self.users_table} u ON sm.from_user_id = u.user_id
            WHERE ta.user_id = :user_id AND lower(sm.status) = 'open'
            ORDER BY sm.created_at DESC
            LIMIT 20
        """
        msg_rows = self.execute_query(messages_query, {"user_id": user_id})
        open_messages = [
            {
                "message_id": int(r["message_id"]),
                "tenant_id": int(r["tenant_id"]),
                "tenant_name": r.get("tenant_name"),
                "from_user_id": int(r["from_user_id"]),
                "from_user_name": r.get("from_user_name"),
                "message": r.get("message") or "",
                "created_at": r.get("created_at"),
            }
            for r in msg_rows
        ]

        # 4. Recent activity for assigned orgs
        activity_query = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                t.business_name AS tenant_name,
                ps.stage,
                CASE 
                    WHEN LOWER(ps.status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
                         AND (
                             (ps.last_heartbeat_at IS NULL AND ps.created_at < (current_timestamp() - INTERVAL 15 MINUTES))
                             OR
                             (ps.last_heartbeat_at IS NOT NULL AND ps.last_heartbeat_at < (current_timestamp() - INTERVAL 15 MINUTES))
                         ) THEN 'stalled'
                    ELSE ps.status
                END AS status,
                ps.error_message,
                ps.created_at AS timestamp
            FROM {self.pipeline_table} ps
            INNER JOIN {self.team_assignments_table} ta ON ps.tenant_id = ta.tenant_id
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            WHERE ta.user_id = :user_id
            ORDER BY ps.created_at DESC
            LIMIT 20
        """
        activity_rows = self.execute_query(activity_query, {"user_id": user_id})
        recent_activity = [
            {
                "batch_id": r.get("batch_id"),
                "tenant_id": int(r["tenant_id"]) if r.get("tenant_id") is not None else None,
                "tenant_name": r.get("tenant_name"),
                "stage": r.get("stage"),
                "status": r.get("status"),
                "error_message": r.get("error_message"),
                "timestamp": r.get("timestamp"),
            }
            for r in activity_rows
        ]

        return {
            "assigned_organizations": assigned_orgs,
            "pipeline_counts": pipeline_counts,
            "open_support_messages": open_messages,
            "recent_activity": recent_activity,
        }

