from typing import Any, Dict, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository):
    """Data access repository for tenant API keys in platform.api_keys."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`api_keys`"

    def create(
        self,
        tenant_id: int,
        key_hash: str,
        key_prefix: str,
    ) -> Dict[str, Any]:
        """Insert a newly hashed API key record. Never stores raw key values."""
        insert_query = f"""
            INSERT INTO {self.table} (
                tenant_id, key_hash, key_prefix, created_at, is_active
            )
            VALUES (
                :tenant_id, :key_hash, :key_prefix, current_timestamp(), true
            )
        """
        params = {
            "tenant_id": tenant_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        }
        self.execute_non_query(insert_query, params)

        select_query = f"""
            SELECT api_key_id, tenant_id, key_hash, key_prefix, created_at, last_used_at, is_active
            FROM {self.table}
            WHERE tenant_id = :tenant_id AND key_hash = :key_hash
            ORDER BY api_key_id DESC
            LIMIT 1
        """
        record = self.execute_single(select_query, {"tenant_id": tenant_id, "key_hash": key_hash})
        if not record:
            raise RuntimeError(f"Failed to retrieve newly created API key record for tenant {tenant_id}")
        return record

    def get_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Look up active API key by its cryptographic SHA-256 hash."""
        query = f"""
            SELECT api_key_id, tenant_id, key_hash, key_prefix, created_at, last_used_at, is_active
            FROM {self.table}
            WHERE key_hash = :key_hash AND is_active = true
            LIMIT 1
        """
        return self.execute_single(query, {"key_hash": key_hash})

    def get_active_by_tenant(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve current active API key metadata for a tenant."""
        query = f"""
            SELECT api_key_id, tenant_id, key_hash, key_prefix, created_at, last_used_at, is_active
            FROM {self.table}
            WHERE tenant_id = :tenant_id AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """
        return self.execute_single(query, {"tenant_id": tenant_id})

    def revoke_by_tenant(self, tenant_id: int) -> None:
        """Deactivate all active API keys belonging to a tenant."""
        query = f"""
            UPDATE {self.table}
            SET is_active = false
            WHERE tenant_id = :tenant_id AND is_active = true
        """
        self.execute_non_query(query, {"tenant_id": tenant_id})

    def update_last_used(self, api_key_id: int) -> None:
        """Update last_used_at timestamp when key authenticates a request."""
        query = f"""
            UPDATE {self.table}
            SET last_used_at = current_timestamp()
            WHERE api_key_id = :api_key_id
        """
        self.execute_non_query(query, {"api_key_id": api_key_id})
