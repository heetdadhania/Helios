from typing import Any, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.core.sorting import DATA_QUALITY_SORT_FIELDS, validate_and_resolve_sort
from app.repositories.data_quality_repository import DataQualityRepository
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
from app.schemas.data_quality import DataQualityLogOut

router = APIRouter()


@router.get(
    "/logs",
    response_model=PaginatedResponse[DataQualityLogOut],
    status_code=status.HTTP_200_OK,
    summary="Get Data Quality Rejection Logs",
    description="Retrieve rejected row logs and hygiene exceptions with server-side pagination. Team Members see assigned tenants; Admins see all.",
)
def get_data_quality_logs(
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID or name filter"),
    batch_id: Optional[str] = Query(None, description="Optional batch UUID filter"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[DataQualityLogOut]:
    """Retrieve operational data quality rejection logs scoped to caller authorization with server-side pagination."""
    order_by = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=DATA_QUALITY_SORT_FIELDS,
        default_clause="d.logged_at DESC",
    )
    repo = DataQualityRepository(cursor)
    raw_res = repo.list_logs(
        user_id=current_user.id,
        user_role=current_user.role.value,
        tenant_filter=tenant_id,
        batch_filter=batch_id,
        page=page,
        page_size=page_size,
        order_by=order_by,
    )
    if isinstance(raw_res, tuple) and len(raw_res) == 2:
        raw_logs, total = raw_res
    else:
        raw_logs = raw_res
        total = len(raw_logs)
    return PaginatedResponse[DataQualityLogOut](
        items=[DataQualityLogOut(**log) for log in raw_logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/rejected-rows/{batch_id}.csv",
    status_code=status.HTTP_200_OK,
    summary="Download Rejected Rows CSV",
    description="Export a CSV of rows excluded in Silver for a specific batch. Scoped to assigned organizations for team members, open to admins.",
)
@router.get(
    "/rejected-rows/{batch_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def download_rejected_rows_csv(
    batch_id: str,
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> Response:
    """Download quarantined rejected records as a UTF-8 with BOM CSV."""
    clean_batch_id = batch_id[:-4] if batch_id.endswith(".csv") else batch_id
    repo = DataQualityRepository(cursor)
    csv_text = repo.get_rejected_rows_csv(
        batch_id=clean_batch_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
    )
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="rejected_rows_{clean_batch_id}.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
