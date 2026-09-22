from typing import Any, Dict, Optional
from databricks.sql.client import Cursor
from app.core.config import settings
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """
    Data access repository for platform.users stored in Databricks Unity Catalog.
    
    Manages accounts, roles, and credential lookup.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`users`"

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch a single user record by unique email address."""
        clean_email = email.strip().lower()
        query = f"SELECT * FROM {self.table} WHERE lower(email) = :email LIMIT 1"
        return self.execute_single(query, {"email": clean_email})

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a user record by primary key user_id."""
        query = f"SELECT * FROM {self.table} WHERE user_id = :user_id LIMIT 1"
        return self.execute_single(query, {"user_id": user_id})

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
