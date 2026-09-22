from fastapi import APIRouter, Depends, File, UploadFile, status
from databricks.sql.client import Cursor

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut
from app.schemas.upload import UploadResponse, UploadStatusOut
from app.services.upload_service import UploadService

router = APIRouter()


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Ingestion File",
    description="Accept multipart .csv or .xlsx file, validate contents, save to UC Volume, and initialize pipeline tracking.",
)
async def upload_file(
    file: UploadFile = File(..., description="Ingestion dataset in .csv or .xlsx format (max 10MB)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> UploadResponse:
    """
    Ingest a new batch file for the authenticated SMB Owner's tenant.
    
    Delegates all validation, storage, and persistence logic to UploadService.
    """
    repo = UploadRepository(cursor)
    return await UploadService.process_upload(
        file=file,
        current_user=current_user,
        repo=repo,
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
