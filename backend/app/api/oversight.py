from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, Response, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.oversight_repository import OversightRepository
from app.schemas.auth import UserOut
from app.schemas.oversight import (
    PlatformUsageResponse,
    TenantCompareRequest,
    TenantCompareResponse,
    TenantDashboardViewAs,
    TenantHealthListResponse,
    AdminHomeResponse,
)
from app.services.oversight_service import OversightService

router = APIRouter()


@router.get(
    "/dashboard/{tenant_id}",
    response_model=TenantDashboardViewAs,
    status_code=status.HTTP_200_OK,
    summary="View-As Tenant Dashboard (Admin)",
    description=(
        "View-as: Execute customer dashboard metrics explicitly scoped to an arbitrary tenant_id. "
        "Accessible only by platform Administrators. Reuses Gold layer fact tables and "
        "dashboard repository queries without duplicating query logic."
    ),
)
def get_tenant_dashboard_view_as(
    tenant_id: int,
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TenantDashboardViewAs:
    """
    Return comprehensive View-As dashboard for specified tenant organization.
    """
    dashboard_repo = DashboardRepository(cursor)
    oversight_repo = OversightRepository(cursor)
    return OversightService.get_tenant_dashboard_view_as(
        tenant_id=tenant_id,
        days=days,
        dashboard_repo=dashboard_repo,
        oversight_repo=oversight_repo,
    )


@router.get(
    "/tenant-health",
    response_model=TenantHealthListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Tenant Health Indicators (Admin)",
    description=(
        "Compute operational health status ('good', 'needs_attention', 'critical') across all registered tenants. "
        "Derived from explainable rules evaluating latest pipeline execution status and fulfillment late delivery rates."
    ),
)
def get_tenant_health(
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TenantHealthListResponse:
    """
    Return system-wide tenant health assessments and breach explanations.
    """
    dashboard_repo = DashboardRepository(cursor)
    oversight_repo = OversightRepository(cursor)
    return OversightService.get_tenant_health(
        oversight_repo=oversight_repo,
        dashboard_repo=dashboard_repo,
        days=days,
    )


@router.post(
    "/compare",
    response_model=TenantCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Tenants Side-by-Side (Admin)",
    description=(
        "Compare key performance indicators (gross revenue, order volume, average basket size, "
        "and late delivery percentage) for 2 or more tenant organizations side by side."
    ),
)
def compare_tenants(
    payload: TenantCompareRequest,
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TenantCompareResponse:
    """
    Evaluate comparative performance metrics across selected tenants.
    """
    dashboard_repo = DashboardRepository(cursor)
    oversight_repo = OversightRepository(cursor)
    return OversightService.compare_tenants(
        tenant_ids=payload.tenant_ids,
        days=payload.days,
        dashboard_repo=dashboard_repo,
        oversight_repo=oversight_repo,
    )


@router.get(
    "/usage",
    response_model=PlatformUsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Platform Usage Trends (Admin)",
    description=(
        "Retrieve platform activity and volume trends built strictly from internal pipeline and audit tables "
        "(runs per day, batches processed per tenant, and total rows ingested over time)."
    ),
)
def get_platform_usage(
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> PlatformUsageResponse:
    """
    Return aggregated platform ingestion and run volume metrics.
    """
    oversight_repo = OversightRepository(cursor)
    return OversightService.get_platform_usage(oversight_repo=oversight_repo)


@router.get(
    "/audit-export",
    status_code=status.HTTP_200_OK,
    summary="Download Unified Audit & Data Quality CSV (Admin)",
    description=(
        "Export a system-wide CSV file combining meta.etl_audit_log and meta.data_quality_log entries "
        "within the specified date range."
    ),
)
def export_audit_log(
    start_date: Optional[str] = Query(None, description="Start date filter in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date filter in YYYY-MM-DD format"),
    current_user: UserOut = Depends(require_role("admin")),
    cursor: Cursor = Depends(get_db_cursor),
) -> Response:
    """
    Generate and stream unified CSV file of ETL audit and data quality rejection logs.
    """
    oversight_repo = OversightRepository(cursor)
    content, media_type, filename = OversightService.generate_audit_export_csv(
        start_date=start_date,
        end_date=end_date,
        oversight_repo=oversight_repo,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=content, media_type=media_type, headers=headers)


@router.get(
    "/home",
    response_model=AdminHomeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Admin Home Operational Dashboard",
    description=(
        "Retrieve system-wide summary counts, top 10 organization revenues over their last 30 days of data, "
        "pipeline runs per day for the last 14 days split into success and failed, "
        "and 10-row tables for organizations and recent pipeline activity. "
        "Executed with parallel subqueries, cached for 30 seconds."
    ),
)
def get_admin_home(
    force_refresh: bool = Query(False, description="Bypass in-memory cache and recompute immediately"),
    current_user: UserOut = Depends(require_role("admin")),
) -> AdminHomeResponse:
    """Consolidated Admin Home metrics with 30s cache and parallel execution."""
    return OversightService.get_admin_home_data(force_refresh=force_refresh)
