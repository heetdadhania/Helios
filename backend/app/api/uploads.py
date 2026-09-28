from typing import Any, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.core.dependencies import get_db_cursor, require_role
from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut
from app.schemas.upload import UploadResponse, UploadStatusOut
from app.services.upload_service import UploadService

router = APIRouter()


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
                detail=f"Access denied: Team member is not assigned to manage tenant {tenant_id}.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Operation requires team_member or admin role.",
    )


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Ingestion File",
    description="Accept multipart .csv or .xlsx file, validate contents, save to UC Volume, and initialize pipeline tracking.",
)
async def upload_file(
    file: UploadFile = File(..., description="Ingestion dataset in .csv or .xlsx format (max 10MB)"),
    tenant_id: Optional[int] = Form(None, description="Target tenant ID on whose behalf the file is uploaded"),
    tenant_id_query: Optional[int] = Query(None, alias="tenant_id", description="Target tenant ID query parameter fallback"),
    current_user: UserOut = Depends(require_role("team_member", "admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> UploadResponse:
    """
    Ingest a new batch file on behalf of a tenant by Team Member or Admin.
    
    Verifies tenant assignment for Team Member callers, and delegates all validation,
    storage, and persistence logic to UploadService.
    """
    target_tenant_id = tenant_id if tenant_id is not None else tenant_id_query
    if target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required in request body/form.",
        )

    verify_team_member_tenant_access(cursor, current_user, target_tenant_id)

    repo = UploadRepository(cursor)
    return await UploadService.process_upload(
        file=file,
        current_user=current_user,
        repo=repo,
        tenant_id=target_tenant_id,
    )


@router.get(
    "/{upload_id}/status",
    response_model=UploadStatusOut,
    status_code=status.HTTP_200_OK,
    summary="Get Upload Pipeline Status",
    description="Retrieve simplified customer-friendly status for an upload batch without exposing pipeline internals.",
)
def get_upload_status(
    upload_id: int,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> UploadStatusOut:
    """
    Return simplified status (Processing, Ready, Failed) for a tenant's upload record.
    """
    repo = UploadRepository(cursor)
    return UploadService.get_upload_status(
        upload_id=upload_id,
        current_user=current_user,
        repo=repo,
    )
