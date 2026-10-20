import logging
import time
from typing import Any, Dict, Optional
from databricks.sql.client import Cursor
from app.core.config import settings
from app.db.base import databricks_cursor
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Data access repository for platform.users stored in Databricks Unity Catalog.
    
    Manages accounts, roles, and credential lookup.
    """

    def __init__(self, cursor: Optional[Cursor] = None, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`users`"

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

    @staticmethod
    def _normalize_user(user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Ensure boolean and counter columns have sensible non-null defaults."""
        if not user:
            return None
        if user.get("failed_login_count") is None:
            user["failed_login_count"] = 0
        if user.get("must_change_password") is None:
            user["must_change_password"] = False
        if user.get("is_active") is None:
            user["is_active"] = True
        return user

    def get_by_email(
        self,
        email: str,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single user record by unique email address with retry-with-backoff
        specifically around the Databricks query to absorb transient warehouse wake-up delays.
        """
        clean_email = email.strip().lower()
        query = f"SELECT {self.USER_COLUMNS} FROM {self.table} WHERE lower(email) = :email LIMIT 1"
        parameters = {"email": clean_email}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    res = self.execute_single(query, parameters)
                    return self._normalize_user(res)

                # On retry or when original cursor fails/is unavailable, use a fresh connection & cursor
                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    res = repo.execute_single(query, parameters)
                    return self._normalize_user(res)
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    backoff = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient error fetching user record on attempt %d/%d [email=%s]: %s. Retrying in %.1fs...",
                        attempt,
                        max_retries,
                        clean_email,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "All %d attempts to fetch user record failed [email=%s]. Last error: %s",
                        max_retries,
                        clean_email,
                        exc,
                    )
                    raise exc

        if last_exception:
            raise last_exception
        return None

    def get_by_id(
        self,
        user_id: int,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a user record by primary key user_id with retry-with-backoff."""
        query = f"SELECT {self.USER_COLUMNS} FROM {self.table} WHERE user_id = :user_id LIMIT 1"
        parameters = {"user_id": user_id}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    res = self.execute_single(query, parameters)
                    return self._normalize_user(res)

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    res = repo.execute_single(query, parameters)
                    return self._normalize_user(res)
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    backoff = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient error fetching user by ID on attempt %d/%d [user_id=%d]: %s. Retrying in %.1fs...",
                        attempt,
                        max_retries,
                        user_id,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "All %d attempts to fetch user by ID failed [user_id=%d]. Last error: %s",
                        max_retries,
                        user_id,
                        exc,
                    )
                    raise exc

        if last_exception:
            raise last_exception
        return None

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new provisioned user into platform.users Delta table.
        
        Accounts can only be created by Admin or Team Member.
        """
        clean_email = email.strip().lower()
        query = f"""
            INSERT INTO {self.table} (tenant_id, name, email, password_hash, role, is_active, created_at)
            VALUES (:tenant_id, :name, :email, :password_hash, :role, true, current_timestamp())
        """
        self.execute_non_query(
            query,
            {
                "tenant_id": tenant_id,
                "name": name.strip(),
                "email": clean_email,
                "password_hash": password_hash,
                "role": role,
            },
        )
        created_user = self.get_by_email(clean_email)
        if not created_user:
            raise RuntimeError(f"User creation failed for {clean_email}")
        return created_user

    def update_password(
        self,
        user_id: int,
        password_hash: str,
        must_change_password: bool = False,
    ) -> None:
        """Update password hash and reset must_change_password flag for a user."""
        query = f"""
            UPDATE {self.table}
            SET password_hash = :password_hash,
                must_change_password = :must_change_password,
                failed_login_count = 0,
                locked_until = NULL,
                password_changed_at = current_timestamp()
            WHERE user_id = :user_id
        """
        self.execute_non_query(
            query,
            {
                "user_id": user_id,
                "password_hash": password_hash,
                "must_change_password": must_change_password,
            },
        )

    def record_login_success(self, user_id: int) -> None:
        """
        Record timestamp of successful authentication and reset failed attempts and lockout.
        """
        query = f"""
            UPDATE {self.table}
            SET last_login_at = current_timestamp(),
                failed_login_count = 0,
                locked_until = NULL
            WHERE user_id = :user_id
        """
        self.execute_non_query(query, {"user_id": user_id})

    def record_failed_attempt(self, user_id: int, new_count: int, lock_until: bool = False) -> None:
        """
        Record a real wrong-password attempt. If lock_until is True, lock account for 15 minutes.
        """
        if lock_until:
            query = f"""
                UPDATE {self.table}
                SET failed_login_count = :failed_count,
                    locked_until = current_timestamp() + INTERVAL 15 MINUTES
                WHERE user_id = :user_id
            """
        else:
            query = f"""
                UPDATE {self.table}
                SET failed_login_count = :failed_count
                WHERE user_id = :user_id
            """
        self.execute_non_query(query, {"user_id": user_id, "failed_count": new_count})

    def reset_password(self, user_id: int, password_hash: str) -> None:
        """
        Reset user password to a newly generated hash, set must_change_password to true,
        and clear failed attempts and lockout.
        """
        query = f"""
            UPDATE {self.table}
            SET password_hash = :password_hash,
                must_change_password = true,
                failed_login_count = 0,
                locked_until = NULL,
                password_changed_at = current_timestamp()
            WHERE user_id = :user_id
        """
        self.execute_non_query(
            query,
            {
                "user_id": user_id,
                "password_hash": password_hash,
            },
        )

    def write_audit_log(
        self,
        actor_user_id: Optional[int],
        actor_role: Optional[str],
        action: str,
        tenant_id: Optional[int] = None,
        reason: Optional[str] = None,
        details_json: Optional[str] = None,
    ) -> None:
        """Insert immutable administrative or security audit row into meta.audit_trail."""
        audit_table = f"`{self.catalog}`.`meta`.`audit_trail`"
        query = f"""
            INSERT INTO {audit_table} (
                occurred_at, actor_user_id, actor_role, action, tenant_id, batch_id, reason, details_json
            )
            VALUES (
                current_timestamp(), :actor_user_id, :actor_role, :action, :tenant_id, NULL, :reason, :details_json
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
                    "reason": reason,
                    "details_json": details_json,
                },
            )
        except Exception as exc:
            logger.error("Failed to write to meta.audit_trail: %s", exc)

    def get_owner_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch the current SMB owner for a given tenant.
        Prefers active owner, then latest created owner by user_id.
        """
        query = f"""
            SELECT {self.USER_COLUMNS} FROM {self.table}
            WHERE tenant_id = :tenant_id AND role = 'smb_owner'
            ORDER BY is_active DESC, user_id DESC
            LIMIT 1
        """
        res = self.execute_single(query, {"tenant_id": int(tenant_id)})
        return self._normalize_user(res)

    def update_owner_details(
        self,
        user_id: int,
        name: str,
        email: str,
        phone_number: str,
    ) -> None:
        """Update display name, email, and phone number for an SMB Owner."""
        query = f"""
            UPDATE {self.table}
            SET name = :name,
                email = :email,
                phone_number = :phone_number
            WHERE user_id = :user_id
        """
        self.execute_non_query(
            query,
            {
                "user_id": int(user_id),
                "name": name.strip(),
                "email": email.strip().lower(),
                "phone_number": phone_number.strip(),
            },
        )

    def toggle_user_active(self, user_id: int, is_active: bool) -> None:
        """Update active status of a user."""
        query = f"UPDATE {self.table} SET is_active = :is_active WHERE user_id = :user_id"
        self.execute_non_query(query, {"user_id": int(user_id), "is_active": is_active})


