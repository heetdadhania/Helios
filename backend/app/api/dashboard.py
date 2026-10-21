import json
import logging
import os
import time
from typing import Any, Callable, Optional, TypeVar
from fastapi import APIRouter, Depends, Query, Response, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DiscountVsProfitResponse,
    LateDeliveryRiskResponse,
    RevenueTrendResponse,
    ShippingModeComparisonResponse,
    TopProductsResponse,
)
from app.services.dashboard_service import DashboardService

logger = logging.getLogger("helios.api.dashboard")

ENABLE_TIMING_LOGS = os.getenv("ENABLE_TIMING_LOGS", "true").lower() in ("true", "1", "yes")

T = TypeVar("T")


def execute_with_timing(
    endpoint_name: str,
    cursor: Any,
    query_fn: Callable[[], T],
    response: Optional[Response] = None,
) -> T:
    """
    Execute dashboard endpoint operation with multi-phase timing instrumentation:
      - Phase (a): acquiring/opening the Databricks connection
      - Phase (b): executing the SQL query itself
      - Phase (c): serializing the response model
    """
    # Phase (a): acquiring/opening the Databricks connection
    t_conn = float(getattr(cursor, "_connection_acquire_time", 0.0) or 0.0)

    # Phase (b): executing the SQL query itself
    t_query_start = time.perf_counter()
    result = query_fn()
    t_query = time.perf_counter() - t_query_start

    # Phase (c): serializing the response
    t_ser_start = time.perf_counter()
    if hasattr(result, "model_dump_json"):
        _ = result.model_dump_json()
    else:
        _ = json.dumps(result, default=str)
    t_ser = time.perf_counter() - t_ser_start

    total_time = t_conn + t_query + t_ser

    if ENABLE_TIMING_LOGS:
        logger.info(
            "[TIMING] %s | (a) Connection: %.4fs | (b) Query: %.4fs | (c) Serialization: %.4fs | Total: %.4fs",
            endpoint_name,
            t_conn,
            t_query,
            t_ser,
            total_time,
        )

    if response is not None:
        response.headers["X-Timing-Connection"] = f"{t_conn:.4f}"
        response.headers["X-Timing-Query"] = f"{t_query:.4f}"
        response.headers["X-Timing-Serialization"] = f"{t_ser:.4f}"
        response.headers["X-Timing-Total"] = f"{total_time:.4f}"

    return result


router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Organization Dashboard Summary",
    description="Retrieve high-level overview metrics, data as of date, and latest submission status for the authenticated SMB Owner.",
)
def get_dashboard_summary(
    response: Response,
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DashboardSummaryResponse:
    """
    Return high-level summary metrics for the Organization Owner's home page.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/summary",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_dashboard_summary(current_user=current_user, repo=repo),
        response=response,
    )



@router.get(
    "/revenue-trend",
    response_model=RevenueTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Daily Revenue Trend",
    description="Retrieve pre-aggregated daily revenue, order volume, and average order value for authenticated tenant.",
)
def get_revenue_trend(
    response: Response,
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> RevenueTrendResponse:
    """
    Return daily time-series revenue metrics using gold.fact_orders_daily_summary.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/revenue-trend",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_revenue_trend(current_user=current_user, days=days, repo=repo),
        response=response,
    )


@router.get(
    "/top-products",
    response_model=TopProductsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Top Selling Products",
    description="Retrieve top products by gross revenue with units sold and order counts.",
)
def get_top_products(
    response: Response,
    limit: int = Query(10, ge=1, le=100, description="Maximum products to return"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TopProductsResponse:
    """
    Return ranked top products for the authenticated SMB Owner's tenant.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/top-products",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_top_products(current_user=current_user, limit=limit, repo=repo, days=days),
        response=response,
    )


@router.get(
    "/late-delivery-risk",
    response_model=LateDeliveryRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fulfillment SLA & Late Delivery Risk",
    description="Retrieve shipment volume, late delivery rate, and status breakdown.",
)
def get_late_delivery_risk(
    response: Response,
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> LateDeliveryRiskResponse:
    """
    Return delivery risk metrics and SLA performance for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/late-delivery-risk",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_late_delivery_risk(current_user=current_user, repo=repo, days=days),
        response=response,
    )


@router.get(
    "/discount-vs-profit",
    response_model=DiscountVsProfitResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Discount vs Profit Margin Analysis",
    description="Evaluate profit margin and discount sensitivity across tiered discount brackets.",
)
def get_discount_vs_profit(
    response: Response,
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DiscountVsProfitResponse:
    """
    Return gross margin analysis across discount tiers for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/discount-vs-profit",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_discount_vs_profit(current_user=current_user, repo=repo, days=days),
        response=response,
    )


@router.get(
    "/shipping-mode-comparison",
    response_model=ShippingModeComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Shipping Mode Performance Comparison",
    description="Compare transit speed, shipment volume, and on-time fulfillment rates across carriers.",
)
def get_shipping_mode_comparison(
    response: Response,
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> ShippingModeComparisonResponse:
    """
    Return comparative fulfillment performance by carrier mode for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return execute_with_timing(
        endpoint_name="/shipping-mode-comparison",
        cursor=cursor,
        query_fn=lambda: DashboardService.get_shipping_mode_comparison(current_user=current_user, repo=repo, days=days),
        response=response,
    )
