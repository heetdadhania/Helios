from typing import Any, Dict, List, Optional
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository):
    """Data access repository for Tenant metadata stored in Delta tables."""

    def get_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Fetch tenant record by its numeric identifier."""
        query = "SELECT * FROM helios_metadata.tenants WHERE id = :id LIMIT 1"
        return self.execute_single(query, {"id": tenant_id})

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Fetch tenant record by its unique slug identifier."""
        query = "SELECT * FROM helios_metadata.tenants WHERE slug = :slug LIMIT 1"
        return self.execute_single(query, {"slug": slug})

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve paginated list of tenant records."""
        query = "SELECT * FROM helios_metadata.tenants ORDER BY id DESC LIMIT :limit OFFSET :offset"
        return self.execute_query(query, {"limit": limit, "offset": offset})

    def create(
        self,
        name: str,
        slug: str,
        catalog_name: str,
        schema_name: str = "default",
    ) -> Dict[str, Any]:
        """Insert a new tenant entry into Delta metadata table."""
        query = """
            INSERT INTO helios_metadata.tenants (name, slug, catalog_name, schema_name, is_active, created_at, updated_at)
            VALUES (:name, :slug, :catalog_name, :schema_name, true, current_timestamp(), current_timestamp())
        """
        self.execute_non_query(
            query,
            {
                "name": name,
                "slug": slug,
                "catalog_name": catalog_name,
                "schema_name": schema_name,
            },
        )
        return self.get_by_slug(slug) or {
            "name": name,
            "slug": slug,
            "catalog_name": catalog_name,
            "schema_name": schema_name,
        }
