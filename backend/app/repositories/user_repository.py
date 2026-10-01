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
        query = f"SELECT * FROM {self.table} WHERE lower(email) = :email LIMIT 1"
        parameters = {"email": clean_email}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    return self.execute_single(query, parameters)

                # On retry or when original cursor fails/is unavailable, use a fresh connection & cursor
                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    return repo.execute_single(query, parameters)
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
        query = f"SELECT * FROM {self.table} WHERE user_id = :user_id LIMIT 1"
        parameters = {"user_id": user_id}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    return self.execute_single(query, parameters)

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    return repo.execute_single(query, parameters)
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
