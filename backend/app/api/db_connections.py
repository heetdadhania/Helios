from typing import Any, List
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.db_connection_repository import DbConnectionRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut
from app.schemas.db_connection import (
    DbConnectionCreate,
    DbConnectionOut,
    DbConnectionTestResult,
)
from app.schemas.upload import UploadResponse
from app.services.db_connection_service import DbConnectionService

router = APIRouter()


@router.post(
    "/test",
    response_model=DbConnectionTestResult,
    status_code=status.HTTP_200_OK,
    summary="Test External Database Connection",
    description="Verify connectivity, TLS negotiation, and credentials without persisting passwords.",
)
def test_connection(
    conn_in: DbConnectionCreate,
    current_user: UserOut = Depends(require_role("smb_owner")),
) -> DbConnectionTestResult:
    """Test remote database connectivity using provided credentials and SELECT 1 query."""
    return DbConnectionService.test_connection(
        db_type=conn_in.db_type,
        host=conn_in.host,
        port=conn_in.port,
        database_name=conn_in.database_name,
        username=conn_in.username,
        password=conn_in.password,
    )


@router.post(
    "",
    response_model=DbConnectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Database Connection",
    description="Save database connection metadata and store credentials in Databricks Secrets.",
)
def create_connection(
    conn_in: DbConnectionCreate,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DbConnectionOut:
    """Store connection metadata in platform tables and credentials in Databricks Secrets."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must be assigned to an active tenant.",
        )

    repo = DbConnectionRepository(cursor)
    return DbConnectionService.save_connection(
        conn_in=conn_in,
        tenant_id=current_user.tenant_id,
        repo=repo,
    )


@router.get(
    "",
    response_model=List[DbConnectionOut],
    status_code=status.HTTP_200_OK,
    summary="List Database Connections",
    description="List all saved database connections for the authenticated SMB Owner's tenant.",
)
def list_connections(
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[DbConnectionOut]:
    """Retrieve all non-sensitive database connection configurations for the tenant."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must be assigned to an active tenant.",
        )

    repo = DbConnectionRepository(cursor)
    records = repo.list_by_tenant(tenant_id=current_user.tenant_id)
    return [
        DbConnectionOut(
            connection_id=int(r["connection_id"]),
            tenant_id=int(r["tenant_id"]),
            db_type=str(r["db_type"]),
            host=str(r["host"]),
            port=int(r["port"]),
            database_name=str(r["database_name"]),
            username=str(r["username"]),
            table_or_query=str(r["table_or_query"]),
            last_synced_at=r.get("last_synced_at"),
            created_at=r.get("created_at"),
            is_active=bool(r.get("is_active", True)),
        )
        for r in records
    ]


@router.post(
    "/{connection_id}/sync",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand Database Sync",
    description="Fetch credentials ephemerally, pull source data, and land in Bronze storage.",
)
def sync_connection(
    connection_id: int,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> UploadResponse:
    """Execute live data sync, land dataset into Bronze volume, and register batch tracking."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user must be assigned to an active tenant.",
        )

    repo = DbConnectionRepository(cursor)
    upload_repo = UploadRepository(cursor)

    return DbConnectionService.sync_now(
        connection_id=connection_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        repo=repo,
        upload_repo=upload_repo,
    )
