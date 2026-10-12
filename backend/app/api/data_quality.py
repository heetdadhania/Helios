from typing import Any, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.repositories.data_quality_repository import DataQualityRepository
from app.schemas.auth import UserOut
from app.schemas.data_quality import DataQualityLogOut

router = APIRouter()


@router.get(
    "/logs",
    response_model=List[DataQualityLogOut],
    status_code=status.HTTP_200_OK,
    summary="Get Data Quality Rejection Logs",
    description="Retrieve rejected row logs and hygiene exceptions. Team Members see assigned tenants; Admins see all.",
)
def get_data_quality_logs(
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID or name filter"),
    batch_id: Optional[str] = Query(None, description="Optional batch UUID filter"),
    limit: int = Query(100, ge=1, le=500, description="Max logs to return"),
    current_user: UserOut = Depends(require_team_or_admin),
    cursor: Cursor = Depends(get_db_cursor),
) -> List[DataQualityLogOut]:
    """Retrieve operational data quality rejection logs scoped to caller authorization."""
    repo = DataQualityRepository(cursor)
    raw_logs = repo.list_logs(
        user_id=current_user.id,
        user_role=current_user.role.value,
        tenant_filter=tenant_id,
        batch_filter=batch_id,
        limit=limit,
    )
    return [DataQualityLogOut(**log) for log in raw_logs]
