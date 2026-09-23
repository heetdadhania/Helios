from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.repositories.base import BaseRepository


class DbConnectionRepository(BaseRepository):
    """Data access repository for database connections in platform.db_connections."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`db_connections`"

    def create(
        self,
        tenant_id: int,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        encrypted_credential_ref: str,
        table_or_query: str,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """Insert a new db connection record. Never writes raw passwords."""
        insert_query = f"""
            INSERT INTO {self.table} (
                tenant_id, db_type, host, port, database_name,
                username, encrypted_credential_ref, table_or_query,
                created_at, is_active
            )
            VALUES (
                :tenant_id, :db_type, :host, :port, :database_name,
                :username, :encrypted_credential_ref, :table_or_query,
                current_timestamp(), :is_active
            )
        """
        params = {
            "tenant_id": tenant_id,
            "db_type": db_type,
            "host": host,
            "port": port,
            "database_name": database_name,
            "username": username,
            "encrypted_credential_ref": encrypted_credential_ref,
            "table_or_query": table_or_query,
            "is_active": is_active,
        }
        self.execute_non_query(insert_query, params)

        select_query = f"""
            SELECT connection_id, tenant_id, db_type, host, port,
                   database_name, username, encrypted_credential_ref,
                   table_or_query, last_synced_at, created_at, is_active
            FROM {self.table}
            WHERE tenant_id = :tenant_id AND encrypted_credential_ref = :encrypted_credential_ref
            ORDER BY connection_id DESC
            LIMIT 1
        """
        record = self.execute_single(
            select_query,
            {"tenant_id": tenant_id, "encrypted_credential_ref": encrypted_credential_ref},
        )
        if not record:
            raise RuntimeError(f"Failed to retrieve newly created DB connection for tenant {tenant_id}")
        return record

    def get_by_id(
        self,
        connection_id: int,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch connection record by ID with optional tenant isolation."""
        if tenant_id is not None:
            query = f"""
                SELECT connection_id, tenant_id, db_type, host, port,
                       database_name, username, encrypted_credential_ref,
                       table_or_query, last_synced_at, created_at, is_active
                FROM {self.table}
                WHERE connection_id = :connection_id AND tenant_id = :tenant_id
                LIMIT 1
            """
            return self.execute_single(query, {"connection_id": connection_id, "tenant_id": tenant_id})

        query = f"""
            SELECT connection_id, tenant_id, db_type, host, port,
                   database_name, username, encrypted_credential_ref,
                   table_or_query, last_synced_at, created_at, is_active
            FROM {self.table}
            WHERE connection_id = :connection_id
            LIMIT 1
        """
        return self.execute_single(query, {"connection_id": connection_id})

    def list_by_tenant(
        self,
        tenant_id: int,
        active_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List all database connections owned by a tenant."""
        where_clause = "WHERE tenant_id = :tenant_id"
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if active_only:
            where_clause += " AND is_active = true"

        query = f"""
            SELECT connection_id, tenant_id, db_type, host, port,
                   database_name, username, encrypted_credential_ref,
                   table_or_query, last_synced_at, created_at, is_active
            FROM {self.table}
            {where_clause}
            ORDER BY created_at DESC
        """
        return self.execute_query(query, params)

    def update_last_synced(
        self,
        connection_id: int,
        tenant_id: Optional[int] = None,
    ) -> None:
        """Update last_synced_at timestamp to current time."""
        if tenant_id is not None:
            query = f"""
                UPDATE {self.table}
                SET last_synced_at = current_timestamp()
                WHERE connection_id = :connection_id AND tenant_id = :tenant_id
            """
            self.execute_non_query(query, {"connection_id": connection_id, "tenant_id": tenant_id})
        else:
            query = f"""
                UPDATE {self.table}
                SET last_synced_at = current_timestamp()
                WHERE connection_id = :connection_id
            """
            self.execute_non_query(query, {"connection_id": connection_id})

    def delete(self, connection_id: int, tenant_id: int) -> bool:
        """Delete a connection record scoped to a tenant."""
        query = f"""
            DELETE FROM {self.table}
            WHERE connection_id = :connection_id AND tenant_id = :tenant_id
        """
        self.execute_non_query(query, {"connection_id": connection_id, "tenant_id": tenant_id})
        return True
