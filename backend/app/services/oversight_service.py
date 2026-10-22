import csv
from datetime import datetime, timezone
import io
import logging
import threading
import time
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
    AdminHomeActivityItem,
    AdminHomeCharts,
    AdminHomeResponse,
    AdminHomeSummary,
    AdminHomeTables,
    DailyPipelineRunStatus,
    OrganizationTableRow,
    RevenueByOrganizationItem,
)
from app.services.dashboard_service import DashboardService, _format_date_as_of

logger = logging.getLogger("helios.services.oversight")


class OversightCache:
    """
    Thread-safe in-memory TTL cache for expensive Admin Oversight aggregations.

    Deliberate Caching Decision:
    Platform-wide aggregations such as tenant health scoring and platform usage
    scan multiple cross-tenant tables and audit logs. When administrators refresh
    or navigate between oversight screens, recomputing these full scans on every
    request creates unnecessary database pressure. A 60-second in-memory TTL
    ensures high responsiveness while keeping operational metrics fresh.
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                timestamp, data = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return data
                del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class OversightService:
    """Service orchestrating Admin-exclusive oversight, cross-tenant observability, and system exports."""

    _cache = OversightCache(ttl_seconds=60.0)
    _home_cache = OversightCache(ttl_seconds=30.0)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached tenant health, platform usage, and admin home aggregations."""
        cls._cache.clear()
        cls._home_cache.clear()

    @classmethod
    def clear_home_cache(cls) -> None:
        """Clear cached Admin Home operational payload."""
        cls._home_cache.clear()

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
                detail=f"Organization with ID {tenant_id} does not exist.",
            )
        tenant_name = tenant_row.get("business_name") or f"Tenant #{tenant_id}"

        # Reuse DashboardService functions so calculation and windowing logic are identical
        from app.services.dashboard_service import DashboardService

        revenue_trend = DashboardService.get_revenue_trend(tenant_id=tenant_id, days=days, repo=dashboard_repo)
        top_products = DashboardService.get_top_products(tenant_id=tenant_id, limit=10, days=days, repo=dashboard_repo)
        late_delivery_risk = DashboardService.get_late_delivery_risk(tenant_id=tenant_id, days=days, repo=dashboard_repo)
        discount_vs_profit = DashboardService.get_discount_vs_profit(tenant_id=tenant_id, days=days, repo=dashboard_repo)
        shipping_modes = DashboardService.get_shipping_mode_comparison(tenant_id=tenant_id, days=days, repo=dashboard_repo)

        return TenantDashboardViewAs(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            days=days,
            data_as_of=revenue_trend.data_as_of,
            revenue_trend=revenue_trend,
            top_products=top_products,
            late_delivery_risk=late_delivery_risk,
            discount_vs_profit=discount_vs_profit,
            shipping_modes=shipping_modes,
        )

    @classmethod
    def get_tenant_health(
        cls,
        oversight_repo: OversightRepository,
        dashboard_repo: Optional[DashboardRepository] = None,
        force_refresh: bool = False,
        days: Optional[int] = None,
    ) -> TenantHealthListResponse:
        """
        Evaluate health status for all tenants using explainable rules against existing pipeline and delivery data.

        Deliberate Caching Decision:
        Results are cached in-memory with a 60-second TTL to avoid repetitive full-table scans
        and window functions across all registered tenants on every admin page load.
        """
        cache_key = f"tenant_health_{days}" if days is not None else "tenant_health"
        if not force_refresh:
            cached = cls._cache.get(cache_key)
            if cached is not None:
                return cached

        tenants = oversight_repo.get_all_tenants()
        latest_pipeline = oversight_repo.get_latest_pipeline_status_per_tenant()

        tenant_ids = [int(t["tenant_id"]) for t in tenants if t.get("tenant_id") is not None]
        anchors: Dict[int, Optional[date]] = {}
        if dashboard_repo is not None and days is not None:
            for tid in tenant_ids:
                anchors[tid] = dashboard_repo.get_latest_data_date(tid) if hasattr(dashboard_repo, "get_latest_data_date") else None

        late_metrics = oversight_repo.get_tenant_late_delivery_rates(
            tenant_ids=tenant_ids if tenant_ids else None,
            days=days,
            anchor_dates=anchors if anchors else None,
        )

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
            batch_id = str(pipe.get("batch_id") or "") if pipe else None
            last_activity = pipe.get("updated_at") if pipe else t.get("created_at")

            batch_label = f"batch {batch_id[:8]}... " if batch_id else ""
            if pipe_status in ("failed", "restart_required"):
                stage_fail = pipe.get("current_stage") or "pipeline"
                issues.append(f"Most recent {batch_label}failed at {stage_fail} stage".replace("  ", " "))
                health_status = "critical"
            elif pipe_status in ("schema_inference_running", "in_progress", "awaiting_confirmation"):
                issues.append(f"Pipeline {batch_label}currently awaiting confirmation / in progress".replace("  ", " "))
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

        response = TenantHealthListResponse(
            total_tenants=len(items),
            critical_count=critical_count,
            needs_attention_count=needs_attention_count,
            good_count=good_count,
            tenants=items,
        )
        cls._cache.set(cache_key, response)
        return response

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

        Performance Optimization:
        Eliminated the N+1 query pattern by replacing loops of individual tenant queries
        with set-based queries fetching all tenant metadata, revenue summaries, and delivery
        metrics in unified batch operations.
        """
        # Batch 1: Fetch metadata for all requested tenants in one query
        tenant_map = oversight_repo.get_tenants_by_ids(tenant_ids)

        # Anchor each tenant to its own latest data date using get_latest_data_date
        anchors: Dict[int, Optional[date]] = {}
        for tid in tenant_ids:
            anchors[tid] = dashboard_repo.get_latest_data_date(tid) if hasattr(dashboard_repo, "get_latest_data_date") else None

        # Batch 2: Fetch revenue totals and order counts in a single set-based query using anchored windows
        rev_map = oversight_repo.get_comparison_revenue_metrics(
            tenant_ids=tenant_ids, days=days, anchor_dates=anchors
        )

        # Batch 3: Fetch shipment counts and late delivery rates in a single set-based query using anchored windows
        ship_map = oversight_repo.get_comparison_delivery_metrics(
            tenant_ids=tenant_ids, days=days, anchor_dates=anchors
        )

        metrics: List[TenantComparisonMetric] = []
        for tid in sorted(tenant_ids):
            tenant_row = tenant_map.get(tid)
            tenant_name = tenant_row.get("business_name") if tenant_row else f"Tenant #{tid}"
            tier = tenant_row.get("tier") if tenant_row else "starter"

            rev_row = rev_map.get(tid, {})
            tot_rev = float(rev_row.get("total_revenue", 0.0) or 0.0)
            tot_orders = int(rev_row.get("total_orders", 0) or 0)
            aov = round(float(tot_rev / tot_orders), 2) if tot_orders > 0 else 0.0

            ship_row = ship_map.get(tid, {})
            tot_shipments = int(ship_row.get("total_shipments", 0) or 0)
            late_pct = float(ship_row.get("late_pct", 0.0) or 0.0)
            avg_days = float(ship_row.get("avg_shipping_days", 0.0) or 0.0)

            anchor = anchors.get(tid)
            data_as_of = _format_date_as_of(anchor)

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
                    data_as_of=data_as_of,
                )
            )

        return TenantCompareResponse(
            days=days,
            compared_at=datetime.now(timezone.utc),
            tenants=metrics,
        )

    @classmethod
    def get_platform_usage(
        cls,
        oversight_repo: OversightRepository,
        force_refresh: bool = False,
    ) -> PlatformUsageResponse:
        """
        Compile system-wide platform usage trends strictly from internal pipeline and audit tables.

        Deliberate Caching Decision:
        Platform-wide ingestion and pipeline run counts are cached in-memory with a 60-second TTL
        to prevent redundant multi-table aggregations during frequent admin dashboard checks.
        """
        if not force_refresh:
            cached = cls._cache.get("platform_usage")
            if cached is not None:
                return cached

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

        response = PlatformUsageResponse(
            total_runs=totals["total_runs"],
            total_rows_ingested=totals["total_rows_ingested"],
            total_batches=totals["total_batches"],
            active_tenants_count=totals["active_tenants_count"],
            pipeline_runs_per_day=pipeline_runs,
            batches_per_tenant=tenant_batches,
            total_rows_ingested_over_time=daily_rows,
        )
        cls._cache.set("platform_usage", response)
        return response

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

    @classmethod
    def get_admin_home_data(cls, force_refresh: bool = False) -> AdminHomeResponse:
        """
        Consolidated Admin Home operational data.
        Cached in-memory for 30 seconds. Cleared when a pipeline run succeeds or fails.
        Queries run concurrently in parallel threads using isolated Databricks connections.
        """
        cache_key = "admin_home_data"
        if not force_refresh:
            cached = cls._home_cache.get(cache_key)
            if cached is not None:
                return cached

        from concurrent.futures import ThreadPoolExecutor
        from app.db.base import get_databricks_connection

        def run_worker(query_type: str):
            conn = get_databricks_connection()
            cur = conn.cursor()
            try:
                repo = OversightRepository(cur)
                if query_type == "summary":
                    return repo.get_admin_home_summary()
                elif query_type == "top_revenue":
                    return repo.get_admin_home_top_10_revenue()
                elif query_type == "pipeline_runs":
                    return repo.get_admin_home_pipeline_runs_14d()
                elif query_type == "tables":
                    return repo.get_admin_home_tables()
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

        with ThreadPoolExecutor(max_workers=4) as executor:
            fut_summary = executor.submit(run_worker, "summary")
            fut_revenue = executor.submit(run_worker, "top_revenue")
            fut_runs = executor.submit(run_worker, "pipeline_runs")
            fut_tables = executor.submit(run_worker, "tables")

            summary_data = fut_summary.result()
            revenue_data = fut_revenue.result()
            runs_data = fut_runs.result()
            orgs_table, activity_table = fut_tables.result()

        response = AdminHomeResponse(
            summary=AdminHomeSummary(**summary_data),
            charts=AdminHomeCharts(
                revenue_by_organization=[RevenueByOrganizationItem(**r) for r in revenue_data],
                pipeline_runs_per_day=[DailyPipelineRunStatus(**r) for r in runs_data],
            ),
            tables=AdminHomeTables(
                organizations=[OrganizationTableRow(**r) for r in orgs_table],
                recent_activity=[AdminHomeActivityItem(**r) for r in activity_table],
            ),
        )
        cls._home_cache.set(cache_key, response)
        return response
