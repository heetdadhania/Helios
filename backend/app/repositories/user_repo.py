from typing import Any, Dict, Optional
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access repository for User accounts and credentials."""

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user record by unique email address."""
        query = "SELECT * FROM helios_metadata.users WHERE email = :email LIMIT 1"
        return self.execute_single(query, {"email": email})

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user record by primary key."""
        query = "SELECT * FROM helios_metadata.users WHERE id = :id LIMIT 1"
        return self.execute_single(query, {"id": user_id})

    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: Optional[str],
        role: str,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """Insert a new user record into metadata repository."""
        query = """
            INSERT INTO helios_metadata.users (email, hashed_password, full_name, role, tenant_id, is_active, created_at, updated_at)
            VALUES (:email, :hashed_password, :full_name, :role, :tenant_id, true, current_timestamp(), current_timestamp())
        """
        self.execute_non_query(
            query,
            {
                "email": email,
                "hashed_password": hashed_password,
                "full_name": full_name or "",
                "role": role,
                "tenant_id": tenant_id,
            },
        )
        return self.get_by_email(email) or {
            "email": email,
            "full_name": full_name,
            "role": role,
            "tenant_id": tenant_id,
        }
