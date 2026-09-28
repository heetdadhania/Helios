import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut
from app.schemas.dashboard import (
    DeliveryRiskBreakdownItem,
    DiscountProfitBand,
    DiscountVsProfitResponse,
    LateDeliveryRiskResponse,
    RevenueTrendPoint,
    RevenueTrendResponse,
    ShippingModeComparisonItem,
    ShippingModeComparisonResponse,
    TopProductItem,
    TopProductsResponse,
)

logger = logging.getLogger("helios.services.dashboard")


class DashboardService:
    """Service formatting and presenting customer dashboard analytics from the Gold layer."""

    @staticmethod
    def _validate_tenant(current_user: UserOut) -> int:
        """Extract and validate tenant_id from authenticated user JWT context."""
        if current_user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to any tenant.",
            )
        return int(current_user.tenant_id)

    @classmethod
    def get_revenue_trend(
        cls,
        current_user: UserOut,
        days: Optional[int],
        repo: DashboardRepository,
    ) -> RevenueTrendResponse:
        """Fetch daily revenue roll-ups from fact_orders_daily_summary."""
        tenant_id = cls._validate_tenant(current_user)
        raw_points = repo.get_revenue_trend(tenant_id=tenant_id, days=days)

        points: List[RevenueTrendPoint] = []
        total_rev = 0.0
        total_orders = 0

        for r in raw_points:
            rev = float(r.get("total_revenue", 0.0) or 0.0)
            ords = int(r.get("total_orders", 0) or 0)
            aov = float(r.get("avg_order_value", 0.0) or 0.0)
            qty = int(r.get("total_quantity", 0) or 0)

            total_rev += rev
            total_orders += ords

            points.append(
                RevenueTrendPoint(
                    date=str(r.get("date_str", "")),
                    total_revenue=round(rev, 2),
                    total_orders=ords,
                    avg_order_value=round(aov, 2),
                    total_quantity=qty,
                )
            )

        return RevenueTrendResponse(
            days=days,
            total_revenue=round(total_rev, 2),
            total_orders=total_orders,
            points=points,
        )

    @classmethod
    def get_top_products(
        cls,
        current_user: UserOut,
        limit: int,
        repo: DashboardRepository,
        days: Optional[int] = None,
    ) -> TopProductsResponse:
        """Retrieve top revenue products from fact_orders and dim_product."""
        tenant_id = cls._validate_tenant(current_user)
        raw_products = repo.get_top_products(tenant_id=tenant_id, limit=limit, days=days)

        products = [
            TopProductItem(
                product_id=int(p["product_id"]),
                product_name=str(p["product_name"]),
                category=p.get("category"),
                total_revenue=float(p.get("total_revenue", 0.0) or 0.0),
                total_units_sold=int(p.get("total_units_sold", 0) or 0),
                total_orders=int(p.get("total_orders", 0) or 0),
            )
            for p in raw_products
        ]

        return TopProductsResponse(limit=limit, days=days, products=products)

    @classmethod
    def get_late_delivery_risk(
        cls,
        current_user: UserOut,
        repo: DashboardRepository,
        days: Optional[int] = None,
    ) -> LateDeliveryRiskResponse:
        """Calculate fulfillment SLA compliance and status breakdown."""
        tenant_id = cls._validate_tenant(current_user)
        data = repo.get_late_delivery_risk(tenant_id=tenant_id, days=days)
        overview = data.get("overview", {})
        breakdown_raw = data.get("breakdown", [])

        tot_ship = int(overview.get("total_shipments", 0) or 0)
        late_ship = int(overview.get("late_shipments", 0) or 0)
        on_time = int(overview.get("on_time_shipments", 0) or 0)
        avg_days = float(overview.get("avg_shipping_days", 0.0) or 0.0)
        late_pct = round((late_ship / tot_ship * 100.0), 2) if tot_ship > 0 else 0.0

        status_breakdown = [
            DeliveryRiskBreakdownItem(
                status_name=str(b["status_name"]),
                total_shipments=int(b.get("total_shipments", 0) or 0),
                late_shipments=int(b.get("late_shipments", 0) or 0),
                late_rate_pct=float(b.get("late_rate_pct", 0.0) or 0.0),
            )
            for b in breakdown_raw
        ]

        return LateDeliveryRiskResponse(
            total_shipments=tot_ship,
            late_shipments=late_ship,
            on_time_shipments=on_time,
            late_rate_pct=late_pct,
            avg_shipping_days=avg_days,
            days=days,
            status_breakdown=status_breakdown,
        )

    @classmethod
    def get_discount_vs_profit(
        cls,
        current_user: UserOut,
        repo: DashboardRepository,
        days: Optional[int] = None,
    ) -> DiscountVsProfitResponse:
        """Analyze impact of discounts on gross margin across tiers."""
        tenant_id = cls._validate_tenant(current_user)
        raw_bands = repo.get_discount_vs_profit(tenant_id=tenant_id, days=days)

        bands: List[DiscountProfitBand] = []
        tot_rev = 0.0
        tot_disc = 0.0
        tot_prof = 0.0

        for b in raw_bands:
            rev = float(b.get("total_revenue", 0.0) or 0.0)
            disc = float(b.get("total_discount", 0.0) or 0.0)
            prof = float(b.get("total_profit", 0.0) or 0.0)
            cnt = int(b.get("order_count", 0) or 0)

            tot_rev += rev
            tot_disc += disc
            tot_prof += prof

            margin = round((prof / rev * 100.0), 2) if rev > 0 else 0.0

            bands.append(
                DiscountProfitBand(
                    band=str(b["band"]),
                    total_revenue=rev,
                    total_discount=disc,
                    total_profit=prof,
                    profit_margin_pct=margin,
                    order_count=cnt,
                )
            )

        overall_margin = round((tot_prof / tot_rev * 100.0), 2) if tot_rev > 0 else 0.0
        overall_disc_rate = round((tot_disc / (tot_rev + tot_disc) * 100.0), 2) if (tot_rev + tot_disc) > 0 else 0.0

        return DiscountVsProfitResponse(
            overall_profit_margin_pct=overall_margin,
            overall_discount_rate_pct=overall_disc_rate,
            days=days,
            bands=bands,
        )

    @classmethod
    def get_shipping_mode_comparison(
        cls,
        current_user: UserOut,
        repo: DashboardRepository,
        days: Optional[int] = None,
    ) -> ShippingModeComparisonResponse:
        """Compare transit velocity and on-time rate by shipping mode."""
        tenant_id = cls._validate_tenant(current_user)
        raw_modes = repo.get_shipping_mode_comparison(tenant_id=tenant_id, days=days)

        modes = [
            ShippingModeComparisonItem(
                mode_name=str(m["mode_name"]),
                shipment_count=int(m.get("shipment_count", 0) or 0),
                avg_shipping_days=float(m.get("avg_shipping_days", 0.0) or 0.0),
                late_count=int(m.get("late_count", 0) or 0),
                late_rate_pct=float(m.get("late_rate_pct", 0.0) or 0.0),
                on_time_rate_pct=float(m.get("on_time_rate_pct", 0.0) or 0.0),
            )
            for m in raw_modes
        ]

        return ShippingModeComparisonResponse(days=days, modes=modes)
