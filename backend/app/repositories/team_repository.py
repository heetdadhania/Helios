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
