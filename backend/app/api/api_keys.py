from typing import Any, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_ingest import ApiKeyGeneratedOut, ApiKeyOut
from app.schemas.auth import UserOut
from app.services.api_key_service import ApiKeyService

router = APIRouter()


@router.get(
    "",
    response_model=Optional[ApiKeyOut],
    status_code=status.HTTP_200_OK,
    summary="Get Tenant API Key Info",
    description="Retrieve metadata and masked preview of the tenant's active ingestion API key.",
)
def get_api_key(
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> Optional[ApiKeyOut]:
    """Retrieve masked API key details. Full raw key is never stored or returned here."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must be assigned to an active organization.",
        )

    repo = ApiKeyRepository(cursor)
    return ApiKeyService.get_tenant_api_key(tenant_id=current_user.tenant_id, repo=repo)


@router.post(
    "/regenerate",
    response_model=ApiKeyGeneratedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate Tenant API Key",
    description="Revoke previous API keys, generate a new key, and return the raw key once for customer saving.",
)
def regenerate_api_key(
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> ApiKeyGeneratedOut:
    """Invalidate existing keys and generate a new high-entropy API key."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must be assigned to an active organization.",
        )

    repo = ApiKeyRepository(cursor)
    return ApiKeyService.regenerate_api_key(tenant_id=current_user.tenant_id, repo=repo)
