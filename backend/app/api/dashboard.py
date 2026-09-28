from typing import Optional
from fastapi import APIRouter, Depends, Query, status

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.dependencies import get_db_cursor, require_role
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut
from app.schemas.dashboard import (
    DiscountVsProfitResponse,
    LateDeliveryRiskResponse,
    RevenueTrendResponse,
    ShippingModeComparisonResponse,
    TopProductsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "/revenue-trend",
    response_model=RevenueTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Daily Revenue Trend",
    description="Retrieve pre-aggregated daily revenue, order volume, and average order value for authenticated tenant.",
)
def get_revenue_trend(
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> RevenueTrendResponse:
    """
    Return daily time-series revenue metrics using gold.fact_orders_daily_summary.
    """
    repo = DashboardRepository(cursor)
    return DashboardService.get_revenue_trend(current_user=current_user, days=days, repo=repo)


@router.get(
    "/top-products",
    response_model=TopProductsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Top Selling Products",
    description="Retrieve top products by gross revenue with units sold and order counts.",
)
def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Maximum products to return"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> TopProductsResponse:
    """
    Return ranked top products for the authenticated SMB Owner's tenant.
    """
    repo = DashboardRepository(cursor)
    return DashboardService.get_top_products(current_user=current_user, limit=limit, repo=repo, days=days)


@router.get(
    "/late-delivery-risk",
    response_model=LateDeliveryRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fulfillment SLA & Late Delivery Risk",
    description="Retrieve shipment volume, late delivery rate, and status breakdown.",
)
def get_late_delivery_risk(
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> LateDeliveryRiskResponse:
    """
    Return delivery risk metrics and SLA performance for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return DashboardService.get_late_delivery_risk(current_user=current_user, repo=repo, days=days)


@router.get(
    "/discount-vs-profit",
    response_model=DiscountVsProfitResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Discount vs Profit Margin Analysis",
    description="Evaluate profit margin and discount sensitivity across tiered discount brackets.",
)
def get_discount_vs_profit(
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> DiscountVsProfitResponse:
    """
    Return gross margin analysis across discount tiers for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return DashboardService.get_discount_vs_profit(current_user=current_user, repo=repo, days=days)


@router.get(
    "/shipping-mode-comparison",
    response_model=ShippingModeComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Shipping Mode Performance Comparison",
    description="Compare transit speed, shipment volume, and on-time fulfillment rates across carriers.",
)
def get_shipping_mode_comparison(
    days: Optional[int] = Query(None, ge=1, le=365, description="Lookback window in calendar days (all-time if omitted)"),
    current_user: UserOut = Depends(require_role("smb_owner")),
    cursor: Cursor = Depends(get_db_cursor),
) -> ShippingModeComparisonResponse:
    """
    Return comparative fulfillment performance by carrier mode for the authenticated tenant.
    """
    repo = DashboardRepository(cursor)
    return DashboardService.get_shipping_mode_comparison(current_user=current_user, repo=repo, days=days)
