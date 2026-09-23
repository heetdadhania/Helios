from fastapi import APIRouter, Depends, Response, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    from typing import Any
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut
from app.schemas.export import ExportRequest
from app.services.export_service import ExportService

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Export Dashboard Data",
    description="Export revenue trends, top products, or full dashboard view as downloadable CSV or PDF scoped strictly to tenant_id.",
)
def export_dashboard_data(
    request: ExportRequest,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> Response:
    """Generate and return a downloadable CSV or PDF file for the authenticated SMB Owner."""
    repo = DashboardRepository(cursor)
    content, media_type, filename = ExportService.generate_export(
        current_user=current_user,
        request=request,
        repo=repo,
    )

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=content, media_type=media_type, headers=headers)
