from typing import Any
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, status

from app.core.api_key_auth import ApiKeyContext, get_api_key_context
from app.core.dependencies import get_db_cursor
from app.repositories.upload_repository import UploadRepository
from app.schemas.api_ingest import ApiIngestPayload, ApiIngestResponse
from app.services.api_ingest_service import ApiIngestService

router = APIRouter()


@router.post(
    "",
    response_model=ApiIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Push Ingestion Records",
    description="Programmatic ingestion endpoint authenticated via X-Helios-Api-Key header. Lands data into Medallion Bronze.",
)
def ingest_records(
    payload: ApiIngestPayload,
    auth_ctx: ApiKeyContext = Depends(get_api_key_context),
    cursor: Cursor = Depends(get_db_cursor),
) -> ApiIngestResponse:
    """Accept order/shipping JSON records, validate payload, and land into Unity Catalog Bronze volume."""
    upload_repo = UploadRepository(cursor)
    return ApiIngestService.process_api_ingest(
        records=payload.records,
        tenant_id=auth_ctx.tenant_id,
        upload_repo=upload_repo,
    )
