from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore
from app.core.dependencies import get_current_active_user, get_db_cursor
from app.repositories.tenant_repo import TenantRepository
from app.schemas.tenant import TenantCreate, TenantResponse
from app.schemas.user import UserRole
from app.services.rbac_service import RBACService

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_in: TenantCreate,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Register a new tenant organization. Requires Admin privileges."""
    RBACService.require_role(current_user, UserRole.ADMIN)
    repo = TenantRepository(cursor)

    existing = repo.get_by_slug(tenant_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{tenant_in.slug}' already exists.",
        )

    return repo.create(
        name=tenant_in.name,
        slug=tenant_in.slug,
        catalog_name=tenant_in.catalog_name,
        schema_name=tenant_in.schema_name,
    )


@router.get("", response_model=List[Dict[str, Any]])
def list_tenants(
    limit: int = 50,
    offset: int = 0,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List tenants registered on Helios platform. Restricted to Admins."""
    RBACService.require_role(current_user, UserRole.ADMIN)
    repo = TenantRepository(cursor)
    return repo.list_all(limit=limit, offset=offset)


@router.get("/{tenant_id}", response_model=Dict[str, Any])
def get_tenant(
    tenant_id: int,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve details for a specific tenant, enforcing tenant isolation boundaries."""
    RBACService.enforce_tenant_isolation(current_user, str(tenant_id))
    repo = TenantRepository(cursor)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found.",
        )
    return tenant
