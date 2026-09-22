from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class TenantContext:
    """
    Mandatory safety-net helper enforcing explicit tenant_id isolation
    across repository SQL queries, supplementing Unity Catalog row filters.
    """

    def __init__(
        self,
        tenant_id: Optional[int],
        user_role: str,
        user_id: Optional[int] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.user_role = user_role
        self.user_id = user_id

    @property
    def is_admin(self) -> bool:
        """Check if current context has global administrative privileges."""
        return self.user_role == "admin"

    @property
    def is_team_member(self) -> bool:
        """Check if current context belongs to an internal platform operator."""
        return self.user_role in ("team_member", "admin")

    def enforce_tenant_boundary(self, requested_tenant_id: Optional[int]) -> int:
        """
        Validate that the active user is permitted to query the requested tenant data.
        
        Admins and assigned team members may access specific tenants.
        SMB owners can ONLY access their own tenant_id.
        """
        if requested_tenant_id is None:
            if self.tenant_id is not None:
                return self.tenant_id
            if self.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Explicit tenant_id parameter required for multi-tenant scope.",
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenant context assigned to active user.",
            )

        if not self.is_team_member and self.tenant_id != requested_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Boundary violation for tenant {requested_tenant_id}.",
            )

        return requested_tenant_id

    def inject_tenant_filter(
        self,
        base_query: str,
        parameters: Dict[str, Any],
        target_tenant_id: Optional[int] = None,
        table_alias: str = "",
    ) -> tuple[str, Dict[str, Any]]:
        """
        Append explicit tenant_id condition to a SQL query as an engine-level safety net.
        """
        resolved_tenant_id = self.enforce_tenant_boundary(target_tenant_id)
        col_prefix = f"{table_alias}." if table_alias else ""
        condition = f"{col_prefix}tenant_id = :tenant_id"

        updated_params = dict(parameters)
        updated_params["tenant_id"] = resolved_tenant_id

        if "WHERE" in base_query.upper():
            modified_query = f"{base_query} AND {condition}"
        else:
            modified_query = f"{base_query} WHERE {condition}"

        return modified_query, updated_params
