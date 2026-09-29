import csv
from datetime import datetime, timezone
import io
import logging
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.oversight_repository import OversightRepository
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
from app.schemas.oversight import (
    DailyPipelineRunUsage,
    DailyRowsIngestedUsage,
    PlatformUsageResponse,
    TenantBatchUsage,
    TenantCompareResponse,
    TenantComparisonMetric,
    TenantDashboardViewAs,
    TenantHealthItem,
    TenantHealthListResponse,
)

logger = logging.getLogger("helios.services.oversight")


class OversightService:
    """Service orchestrating Admin-exclusive oversight, cross-tenant observability, and system exports."""

    # -----------------------------------------------------------------------------
    # Tenant Health Evaluation Rules & Exact Thresholds:
    # -----------------------------------------------------------------------------
    # 1. Fulfillment SLA & Late Delivery Rate (from gold.fact_shipments):
    #    - CRITICAL: late_delivery_rate_pct >= 25.0%
    #    - NEEDS_ATTENTION: 10.0% <= late_delivery_rate_pct < 25.0%
    #    - GOOD: late_delivery_rate_pct < 10.0% (or no shipments recorded yet)
    #
    # 2. Pipeline Execution Status (from platform.pipeline_status):
    #    - CRITICAL: Latest pipeline run has status='failed' or 'restart_required'
    #                and has not been recovered by a succeeding retry.
    #    - NEEDS_ATTENTION: Latest run is 'in_progress', 'schema_inference_running',
    #                       or 'awaiting_confirmation'.
    #    - GOOD: Latest run succeeded ('success', 'completed'), or no runs yet.
    #
    # 3. Overall Composite Health Status:
    #    - 'critical' if pipeline status is CRITICAL or late delivery rate is CRITICAL.
    #    - 'needs_attention' if pipeline or delivery is NEEDS_ATTENTION (and not critical).
    #    - 'good' otherwise.
    # -----------------------------------------------------------------------------
    LATE_DELIVERY_CRITICAL_THRESHOLD_PCT: float = 25.0
    LATE_DELIVERY_WARNING_THRESHOLD_PCT: float = 10.0

    @classmethod
    def get_tenant_dashboard_view_as(
        cls,
        tenant_id: int,
        days: Optional[int],
        dashboard_repo: DashboardRepository,
        oversight_repo: OversightRepository,
    ) -> TenantDashboardViewAs:
        """
        View-as: Execute customer dashboard queries explicitly scoped to an arbitrary tenant_id.
        Reuses existing DashboardRepository query functions rather than duplicating logic.
        """
        tenant_row = oversight_repo.get_tenant_by_id(tenant_id)
        if not tenant_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant organization with ID {tenant_id} does not exist.",
            )
        tenant_name = tenant_row.get("business_name") or f"Tenant #{tenant_id}"

        # 1. Revenue Trend (reusing dashboard_repo)
        raw_trend = dashboard_repo.get_revenue_trend(tenant_id=tenant_id, days=days)
        trend_points: List[RevenueTrendPoint] = []
        total_rev = 0.0
        total_orders = 0
        for r in raw_trend:
            rev = float(r.get("total_revenue", 0.0) or 0.0)
            ords = int(r.get("total_orders", 0) or 0)
            aov = float(r.get("avg_order_value", 0.0) or 0.0)
            qty = int(r.get("total_quantity", 0) or 0)
            total_rev += rev
            total_orders += ords
            trend_points.append(
                RevenueTrendPoint(
                    date=str(r.get("date_str", "")),
                    total_revenue=round(rev, 2),
                    total_orders=ords,
                    avg_order_value=round(aov, 2),
                    total_quantity=qty,
                )
            )
        revenue_trend = RevenueTrendResponse(
            days=days,
            total_revenue=round(total_rev, 2),
            total_orders=total_orders,
            points=trend_points,
        )

        # 2. Top Products (reusing dashboard_repo)
        raw_prods = dashboard_repo.get_top_products(tenant_id=tenant_id, limit=10, days=days)
        products = [
            TopProductItem(
                product_id=int(p.get("product_id", 0)),
                product_name=str(p.get("product_name", "Unknown")),
                category=p.get("category"),
                total_revenue=float(p.get("total_revenue", 0.0) or 0.0),
                total_units_sold=int(p.get("total_units_sold", 0) or 0),
                total_orders=int(p.get("total_orders", 0) or 0),
            )
            for p in raw_prods
        ]
        top_products = TopProductsResponse(limit=10, days=days, products=products)

        # 3. Late Delivery Risk (reusing dashboard_repo)
        raw_delivery = dashboard_repo.get_late_delivery_risk(tenant_id=tenant_id, days=days)
        ov = raw_delivery.get("overview", {}) or {}
        bd = raw_delivery.get("breakdown", []) or []
        tot_shipments = int(ov.get("total_shipments", 0) or 0)
        late_shipments = int(ov.get("late_shipments", 0) or 0)
        on_time = int(ov.get("on_time_shipments", 0) or 0)
        late_rate = round(float(late_shipments / tot_shipments * 100.0), 2) if tot_shipments > 0 else 0.0
        avg_shipping = float(ov.get("avg_shipping_days", 0.0) or 0.0)

        breakdown_items = [
            DeliveryRiskBreakdownItem(
                status_name=str(b.get("status_name", "Unknown")),
                total_shipments=int(b.get("total_shipments", 0) or 0),
                late_shipments=int(b.get("late_shipments", 0) or 0),
                late_rate_pct=float(b.get("late_rate_pct", 0.0) or 0.0),
            )
            for b in bd
        ]
        late_delivery_risk = LateDeliveryRiskResponse(
            total_shipments=tot_shipments,
            late_shipments=late_shipments,
            on_time_shipments=on_time,
            late_rate_pct=late_rate,
            avg_shipping_days=avg_shipping,
            days=days,
            status_breakdown=breakdown_items,
        )

        # 4. Discount vs Profit (reusing dashboard_repo)
        raw_discount = dashboard_repo.get_discount_vs_profit(tenant_id=tenant_id, days=days)
        bands: List[DiscountProfitBand] = []
        tot_rev_disc = 0.0
        tot_disc_val = 0.0
        tot_prof_val = 0.0
        for b in raw_discount:
            b_rev = float(b.get("total_revenue", 0.0) or 0.0)
            b_disc = float(b.get("total_discount", 0.0) or 0.0)
            b_prof = float(b.get("total_profit", 0.0) or 0.0)
            tot_rev_disc += b_rev
            tot_disc_val += b_disc
            tot_prof_val += b_prof
            margin = round(float(b_prof / b_rev * 100.0), 2) if b_rev > 0 else 0.0
            bands.append(
                DiscountProfitBand(
                    band=str(b.get("band", "0%")),
                    total_revenue=b_rev,
                    total_discount=b_disc,
                    total_profit=b_prof,
                    profit_margin_pct=margin,
                    order_count=int(b.get("order_count", 0) or 0),
                )
            )
        ov_margin = round(float(tot_prof_val / tot_rev_disc * 100.0), 2) if tot_rev_disc > 0 else 0.0
        ov_disc_rate = round(float(tot_disc_val / (tot_rev_disc + tot_disc_val) * 100.0), 2) if (tot_rev_disc + tot_disc_val) > 0 else 0.0
        discount_vs_profit = DiscountVsProfitResponse(
            overall_profit_margin_pct=ov_margin,
            overall_discount_rate_pct=ov_disc_rate,
            days=days,
            bands=bands,
        )

        # 5. Shipping Modes (reusing dashboard_repo)
        raw_shipping = dashboard_repo.get_shipping_mode_comparison(tenant_id=tenant_id, days=days)
        shipping_items = [
            ShippingModeComparisonItem(
                mode_name=str(m.get("mode_name", "Standard")),
                shipment_count=int(m.get("shipment_count", 0) or 0),
                avg_shipping_days=float(m.get("avg_shipping_days", 0.0) or 0.0),
                late_count=int(m.get("late_count", 0) or 0),
                late_rate_pct=float(m.get("late_rate_pct", 0.0) or 0.0),
                on_time_rate_pct=float(m.get("on_time_rate_pct", 100.0) or 100.0),
            )
            for m in raw_shipping
        ]
        shipping_modes = ShippingModeComparisonResponse(modes=shipping_items)

        return TenantDashboardViewAs(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            days=days,
            revenue_trend=revenue_trend,
            top_products=top_products,
            late_delivery_risk=late_delivery_risk,
            discount_vs_profit=discount_vs_profit,
            shipping_modes=shipping_modes,
        )

    @classmethod
    def get_tenant_health(cls, oversight_repo: OversightRepository) -> TenantHealthListResponse:
        """
        Evaluate health status for all tenants using explainable rules against existing pipeline and delivery data.
        """
        tenants = oversight_repo.get_all_tenants()
        latest_pipeline = oversight_repo.get_latest_pipeline_status_per_tenant()
        late_metrics = oversight_repo.get_tenant_late_delivery_rates()

        items: List[TenantHealthItem] = []
        critical_count = 0
        needs_attention_count = 0
        good_count = 0

        for t in tenants:
            tenant_id = int(t["tenant_id"])
            tenant_name = t.get("business_name") or f"Tenant #{tenant_id}"
            slug = t.get("slug") or f"tenant-{tenant_id}"
            tier = t.get("tier") or "starter"

            pipe = latest_pipeline.get(tenant_id)
            ship = late_metrics.get(tenant_id)

            issues: List[str] = []
            health_status = "good"

            # 1. Delivery health check
            late_rate = float(ship.get("late_rate_pct", 0.0) or 0.0) if ship else 0.0
            tot_shipments = int(ship.get("total_shipments", 0) or 0) if ship else 0

            if tot_shipments > 0:
                if late_rate >= cls.LATE_DELIVERY_CRITICAL_THRESHOLD_PCT:
                    issues.append(
                        f"Critical late delivery rate: {late_rate:.1f}% exceeds {cls.LATE_DELIVERY_CRITICAL_THRESHOLD_PCT}% SLA threshold"
                    )
                    health_status = "critical"
                elif late_rate >= cls.LATE_DELIVERY_WARNING_THRESHOLD_PCT:
                    issues.append(
                        f"Elevated late delivery rate: {late_rate:.1f}% exceeds {cls.LATE_DELIVERY_WARNING_THRESHOLD_PCT}% target"
                    )
                    if health_status != "critical":
                        health_status = "needs_attention"

            # 2. Pipeline execution health check
            pipe_status = str(pipe.get("status", "")).lower() if pipe else None
            batch_id = str(pipe.get("batch_id", "")) if pipe else None
            last_activity = pipe.get("updated_at") if pipe else t.get("created_at")

            if pipe_status in ("failed", "restart_required"):
                stage_fail = pipe.get("current_stage") or "pipeline"
                issues.append(f"Most recent batch {batch_id[:8]}... failed at {stage_fail} stage")
                health_status = "critical"
            elif pipe_status in ("schema_inference_running", "in_progress", "awaiting_confirmation"):
                issues.append(f"Pipeline batch {batch_id[:8]}... currently awaiting confirmation / in progress")
                if health_status != "critical":
                    health_status = "needs_attention"

            # Count aggregation
            if health_status == "critical":
                critical_count += 1
            elif health_status == "needs_attention":
                needs_attention_count += 1
            else:
                good_count += 1

            items.append(
                TenantHealthItem(
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    slug=slug,
                    tier=tier,
                    health_status=health_status,
                    latest_pipeline_status=pipe_status,
                    latest_batch_id=batch_id,
                    late_delivery_rate_pct=late_rate,
                    total_shipments=tot_shipments,
                    issues=issues,
                    last_activity_at=last_activity,
                )
            )

        return TenantHealthListResponse(
            total_tenants=len(items),
            critical_count=critical_count,
            needs_attention_count=needs_attention_count,
            good_count=good_count,
            tenants=items,
        )

    @classmethod
    def compare_tenants(
        cls,
        tenant_ids: List[int],
        days: Optional[int],
        dashboard_repo: DashboardRepository,
        oversight_repo: OversightRepository,
    ) -> TenantCompareResponse:
        """
        Return comparative metrics (revenue, late-delivery %, AOV, order count) for 2+ tenants side by side.
        Reuses existing dashboard repository queries.
        """
        metrics: List[TenantComparisonMetric] = []
        for tid in tenant_ids:
            tenant_row = oversight_repo.get_tenant_by_id(tid)
            tenant_name = tenant_row.get("business_name") if tenant_row else f"Tenant #{tid}"
            tier = tenant_row.get("tier") if tenant_row else "starter"

            # Reusing get_revenue_trend
            trend = dashboard_repo.get_revenue_trend(tenant_id=tid, days=days)
            tot_rev = sum(float(r.get("total_revenue", 0.0) or 0.0) for r in trend)
            tot_orders = sum(int(r.get("total_orders", 0) or 0) for r in trend)
            aov = round(float(tot_rev / tot_orders), 2) if tot_orders > 0 else 0.0

            # Reusing get_late_delivery_risk
            risk = dashboard_repo.get_late_delivery_risk(tenant_id=tid, days=days)
            ov = risk.get("overview", {}) or {}
            tot_shipments = int(ov.get("total_shipments", 0) or 0)
            late_shipments = int(ov.get("late_shipments", 0) or 0)
            late_pct = round(float(late_shipments / tot_shipments * 100.0), 2) if tot_shipments > 0 else 0.0
            avg_days = float(ov.get("avg_shipping_days", 0.0) or 0.0)

            metrics.append(
                TenantComparisonMetric(
                    tenant_id=tid,
                    tenant_name=tenant_name,
                    tier=tier,
                    total_revenue=round(tot_rev, 2),
                    total_orders=tot_orders,
                    avg_order_value=aov,
                    total_shipments=tot_shipments,
                    late_delivery_pct=late_pct,
                    avg_shipping_days=avg_days,
                )
            )

        return TenantCompareResponse(
            days=days,
            compared_at=datetime.now(timezone.utc),
            tenants=metrics,
        )

    @classmethod
    def get_platform_usage(cls, oversight_repo: OversightRepository) -> PlatformUsageResponse:
        """
        Compile system-wide platform usage trends strictly from internal pipeline and audit tables.
        """
        totals = oversight_repo.get_overall_usage_totals()
        raw_runs = oversight_repo.get_usage_pipeline_runs_per_day()
        raw_batches = oversight_repo.get_usage_batches_per_tenant()
        raw_rows = oversight_repo.get_usage_rows_ingested_per_day()

        pipeline_runs = [
            DailyPipelineRunUsage(
                date=str(r.get("date_str", "")),
                total_runs=int(r.get("total_runs", 0) or 0),
                successful_runs=int(r.get("successful_runs", 0) or 0),
                failed_runs=int(r.get("failed_runs", 0) or 0),
            )
            for r in raw_runs
        ]

        tenant_batches = [
            TenantBatchUsage(
                tenant_id=int(b.get("tenant_id", 0)),
                tenant_name=str(b.get("tenant_name", "Tenant")),
                batch_count=int(b.get("batch_count", 0) or 0),
                last_batch_at=b.get("last_batch_at"),
            )
            for b in raw_batches
        ]

        daily_rows = [
            DailyRowsIngestedUsage(
                date=str(rw.get("date_str", "")),
                rows_ingested=int(rw.get("rows_ingested", 0) or 0),
            )
            for rw in raw_rows
        ]

        return PlatformUsageResponse(
            total_runs=totals["total_runs"],
            total_rows_ingested=totals["total_rows_ingested"],
            total_batches=totals["total_batches"],
            active_tenants_count=totals["active_tenants_count"],
            pipeline_runs_per_day=pipeline_runs,
            batches_per_tenant=tenant_batches,
            total_rows_ingested_over_time=daily_rows,
        )

    @classmethod
    def generate_audit_export_csv(
        cls,
        start_date: Optional[str],
        end_date: Optional[str],
        oversight_repo: OversightRepository,
    ) -> Tuple[bytes, str, str]:
        """
        Generate downloadable CSV combining meta.etl_audit_log and meta.data_quality_log entries.
        Returns (content_bytes, media_type, filename).
        """
        records = oversight_repo.get_audit_export_records(start_date=start_date, end_date=end_date)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Log Type",
            "Log ID",
            "Timestamp",
            "Batch ID",
            "Tenant ID",
            "Tenant Name",
            "Stage / Table Name",
            "Status / Rejection Reason",
            "Row Count / Row ID",
            "Error Detail",
        ])

        for r in records:
            writer.writerow([
                r.get("log_type", ""),
                r.get("log_id", ""),
                r.get("timestamp", ""),
                r.get("batch_id", ""),
                r.get("tenant_id", ""),
                r.get("tenant_name", ""),
                r.get("stage_or_table", ""),
                r.get("status_or_reason", ""),
                r.get("row_count_or_identifier", ""),
                r.get("error_detail", ""),
            ])

        csv_str = output.getvalue()
        content = csv_str.encode("utf-8-sig")  # Excel-compatible BOM
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"helios_audit_export_{timestamp_str}.csv"
        return content, "text/csv; charset=utf-8", filename
