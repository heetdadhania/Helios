from typing import Any, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
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


class DbConnectionCreateRequest(DbConnectionCreate):
    """Payload to test or save a database connection, accepting an explicit target tenant_id."""

    tenant_id: Optional[int] = Field(
        None,
        description="Target tenant ID on whose behalf the connection is configured",
    )


class DbConnectionSyncRequest(BaseModel):
    """Optional payload to trigger database sync with explicit target tenant_id."""

    tenant_id: Optional[int] = Field(
        None,
        description="Target tenant ID on whose behalf the connection is synced",
    )
    override_duplicate: bool = Field(
        default=False,
        description="Whether to override duplicate submission check",
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Audit reason for duplicate override (min 5 characters)",
    )


def verify_team_member_tenant_access(
    cursor: Cursor,
    current_user: UserOut,
    tenant_id: int,
) -> None:
    """
    Verify caller has permission to perform operations on behalf of the tenant.
    Admin bypasses this check.
    Team Member must have an active assignment in platform.team_assignments.
    """
    user_role = (
        current_user.role.value.lower()
        if hasattr(current_user.role, "value")
        else str(current_user.role).lower()
    )
    if user_role == "admin":
        return

    if user_role == "team_member":
        catalog = getattr(settings, "DATABRICKS_CATALOG", "helios")
        query = f"SELECT 1 FROM `{catalog}`.`platform`.`team_assignments` WHERE user_id = :user_id AND tenant_id = :tenant_id LIMIT 1"
        cursor.execute(query, {"user_id": current_user.id, "tenant_id": tenant_id})
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Team member is not assigned to manage organization {tenant_id}.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Operation requires team_member or admin role.",
    )


@router.post(
    "/test",
    response_model=DbConnectionTestResult,
    status_code=status.HTTP_200_OK,
    summary="Test External Database Connection",
    description="Verify connectivity, TLS negotiation, and credentials without persisting passwords. Operated by Team Member or Admin on behalf of a tenant.",
)
def test_connection(
    conn_in: DbConnectionCreateRequest,
    tenant_id: Optional[int] = Query(None, description="Target tenant ID on whose behalf the test is performed"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DbConnectionTestResult:
    """Test remote database connectivity using provided credentials and SELECT 1 query."""
    target_tenant_id = tenant_id if tenant_id is not None else conn_in.tenant_id
    if target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required in request body or query parameter.",
        )

    verify_team_member_tenant_access(cursor, current_user, target_tenant_id)

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
    description="Save database connection metadata and store credentials in Databricks Secrets. Operated by Team Member or Admin on behalf of a tenant.",
)
def create_connection(
    conn_in: DbConnectionCreateRequest,
    tenant_id: Optional[int] = Query(None, description="Target tenant ID on whose behalf the connection is created"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DbConnectionOut:
    """Store connection metadata in platform tables and credentials in Databricks Secrets."""
    target_tenant_id = tenant_id if tenant_id is not None else conn_in.tenant_id
    if target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required in request body or query parameter.",
        )

    verify_team_member_tenant_access(cursor, current_user, target_tenant_id)

    repo = DbConnectionRepository(cursor)
    return DbConnectionService.save_connection(
        conn_in=conn_in,
        tenant_id=target_tenant_id,
        repo=repo,
        created_by=current_user.id,
    )


@router.get(
    "",
    response_model=List[DbConnectionOut],
    status_code=status.HTTP_200_OK,
    summary="List Database Connections",
    description="List all saved database connections for a specified tenant. Operated by Team Member or Admin.",
)
def list_connections(
    tenant_id: Optional[int] = Query(None, description="Target tenant ID"),
    active_only: bool = Query(True, description="Filter for active connections only"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[DbConnectionOut]:
    """Retrieve all non-sensitive database connection configurations for the tenant."""
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id query parameter is required.",
        )

    verify_team_member_tenant_access(cursor, current_user, tenant_id)

    repo = DbConnectionRepository(cursor)
    records = repo.list_by_tenant(tenant_id=tenant_id, active_only=active_only)
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
    description="Fetch credentials ephemerally, pull source data, and land in Bronze storage. Operated by Team Member or Admin on behalf of a tenant.",
)
def sync_connection(
    connection_id: int,
    tenant_id: Optional[int] = Query(None, description="Target tenant ID on whose behalf sync is executed"),
    override_duplicate: bool = Query(False, description="Whether to override duplicate check"),
    override_reason: Optional[str] = Query(None, description="Override audit reason"),
    payload: Optional[DbConnectionSyncRequest] = None,
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> UploadResponse:
    """Execute live data sync, land dataset into Bronze volume, and register batch tracking."""
    target_tenant_id = tenant_id if tenant_id is not None else (payload.tenant_id if payload else None)
    if target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required in request body or query parameter.",
        )

    verify_team_member_tenant_access(cursor, current_user, target_tenant_id)

    effective_override = (payload.override_duplicate if payload else False) or override_duplicate
    effective_reason = (payload.override_reason if payload else None) or override_reason

    repo = DbConnectionRepository(cursor)
    upload_repo = UploadRepository(cursor)

    return DbConnectionService.sync_now(
        connection_id=connection_id,
        tenant_id=target_tenant_id,
        user_id=current_user.id,
        repo=repo,
        upload_repo=upload_repo,
        override_duplicate=effective_override,
        override_reason=effective_reason,
    )
