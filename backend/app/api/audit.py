"""Audit Trail API endpoints for Administrators."""

import logging
from typing import Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    from typing import Any
    Cursor = Any  # type: ignore

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db_cursor, require_role
from app.core.sorting import AUDIT_SORT_FIELDS, validate_and_resolve_sort
from app.schemas.audit import AuditLogItem
from app.schemas.auth import UserOut
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

logger = logging.getLogger("helios.api.audit")

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogItem],
    status_code=status.HTTP_200_OK,
    summary="Get System Audit Trail (Admin Only)",
    dependencies=[Depends(require_role("admin"))],
    description=(
        "Retrieve paginated administrative and operational audit records from meta.audit_trail. "
        "Strictly restricted to Admin users; returns HTTP 403 for Team Members and SMB Owners. "
        "Supports filtering by date range (start_date, end_date), actor (user ID, name, email, or role), "
        "action descriptor, and organization (tenant_id or business name)."
    ),
)
def get_audit_trail(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    actor: Optional[str] = Query(None, description="Actor filter (user ID, name, email, or role)"),
    action: Optional[str] = Query(None, description="Action filter (e.g. upload, batch_approved, password_reset)"),
    tenant_id: Optional[int] = Query(None, description="Organization / tenant ID filter"),
    organization: Optional[str] = Query(None, description="Organization business name or ID filter"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> PaginatedResponse[AuditLogItem]:
    """Retrieve filtered and paginated audit records for administrators."""
    order_by = validate_and_resolve_sort(
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_fields=AUDIT_SORT_FIELDS,
        default_clause="a.occurred_at DESC, a.audit_id DESC",
    )
    return AuditService.get_audit_trail(
        cursor=cursor,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        actor=actor,
        action=action,
        tenant_id=tenant_id,
        organization=organization,
        order_by=order_by,
    )
