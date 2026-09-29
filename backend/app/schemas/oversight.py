from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.dashboard import (
    DiscountVsProfitResponse,
    LateDeliveryRiskResponse,
    RevenueTrendResponse,
    ShippingModeComparisonResponse,
    TopProductsResponse,
)


# --- 1. View-As Dashboard Schemas ---
class TenantDashboardViewAs(BaseModel):
    """Admin View-As full tenant dashboard representation."""

    tenant_id: int = Field(..., description="Target tenant ID")
    tenant_name: str = Field(..., description="Target tenant business display name")
    days: Optional[int] = Field(None, description="Lookback window in calendar days (None if all-time)")
    revenue_trend: RevenueTrendResponse = Field(..., description="Daily revenue trend metrics")
    top_products: TopProductsResponse = Field(..., description="Ranked top-selling products")
    late_delivery_risk: LateDeliveryRiskResponse = Field(..., description="Fulfillment SLA and delivery metrics")
    discount_vs_profit: DiscountVsProfitResponse = Field(..., description="Discount sensitivity and margins")
    shipping_modes: ShippingModeComparisonResponse = Field(..., description="Shipping channel comparisons")


# --- 2. Tenant Health Schemas ---
class TenantHealthItem(BaseModel):
    """Computed health status for a tenant based on pipeline and delivery metrics."""

    tenant_id: int = Field(..., description="Tenant organization ID")
    tenant_name: str = Field(..., description="Tenant business display name")
    slug: str = Field(..., description="Tenant identifier slug")
    tier: str = Field("starter", description="Tenant service tier: starter, professional, enterprise")
    health_status: str = Field(..., description="Overall health state: good, needs_attention, critical")
    latest_pipeline_status: Optional[str] = Field(None, description="Status of most recent pipeline execution")
    latest_batch_id: Optional[str] = Field(None, description="ID of most recent batch")
    late_delivery_rate_pct: float = Field(0.0, description="Percentage of delayed deliveries (0.0 - 100.0)")
    total_shipments: int = Field(0, description="Total shipments recorded for tenant")
    issues: List[str] = Field(default_factory=list, description="Specific operational issues or breach explanations")
    last_activity_at: Optional[datetime] = Field(None, description="Timestamp of latest activity or pipeline update")

    model_config = {"from_attributes": True}


class TenantHealthListResponse(BaseModel):
    """System-wide tenant health summary list."""

    total_tenants: int = Field(..., description="Total count of tenants evaluated")
    critical_count: int = Field(..., description="Number of tenants in critical state")
    needs_attention_count: int = Field(..., description="Number of tenants needing attention")
    good_count: int = Field(..., description="Number of tenants in good standing")
    tenants: List[TenantHealthItem] = Field(default_factory=list, description="Evaluated tenant health items")


# --- 3. Tenant Comparison Schemas ---
class TenantCompareRequest(BaseModel):
    """Payload to compare multiple tenants side-by-side."""

    tenant_ids: List[int] = Field(
        ...,
        min_length=2,
        description="List of 2 or more tenant IDs to compare",
    )
    days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Optional lookback window in calendar days (all-time if omitted)",
    )


class TenantComparisonMetric(BaseModel):
    """Key comparative performance metrics for an individual tenant."""

    tenant_id: int = Field(..., description="Tenant ID")
    tenant_name: str = Field(..., description="Tenant business display name")
    tier: str = Field("starter", description="Service tier")
    total_revenue: float = Field(0.0, description="Total gross revenue in period")
    total_orders: int = Field(0, description="Total order volume in period")
    avg_order_value: float = Field(0.0, description="Average order basket size")
    total_shipments: int = Field(0, description="Total shipments processed")
    late_delivery_pct: float = Field(0.0, description="Percentage of shipments delayed past SLA")
    avg_shipping_days: float = Field(0.0, description="Mean shipping transit duration in days")


class TenantCompareResponse(BaseModel):
    """Side-by-side comparative metric analysis for requested tenants."""

    days: Optional[int] = Field(None, description="Lookback window in calendar days")
    compared_at: datetime = Field(..., description="Timestamp when comparison was evaluated")
    tenants: List[TenantComparisonMetric] = Field(default_factory=list, description="Tenant comparative metrics")


# --- 4. Platform Usage Schemas ---
class DailyPipelineRunUsage(BaseModel):
    """Daily count of pipeline runs."""

    date: str = Field(..., description="Date YYYY-MM-DD")
    total_runs: int = Field(..., description="Total pipeline executions on this date")
    successful_runs: int = Field(..., description="Successful pipeline completions")
    failed_runs: int = Field(..., description="Failed pipeline runs")


class TenantBatchUsage(BaseModel):
    """Volume of batches processed per tenant."""

    tenant_id: int = Field(..., description="Tenant ID")
    tenant_name: str = Field(..., description="Tenant display name")
    batch_count: int = Field(..., description="Total batches processed for this tenant")
    last_batch_at: Optional[datetime] = Field(None, description="Timestamp of most recent batch")


class DailyRowsIngestedUsage(BaseModel):
    """Daily row ingestion volume."""

    date: str = Field(..., description="Date YYYY-MM-DD")
    rows_ingested: int = Field(..., description="Total rows ingested into Bronze on this date")


class PlatformUsageResponse(BaseModel):
    """System-wide platform ingestion and pipeline usage trends."""

    total_runs: int = Field(..., description="Total lifetime pipeline runs recorded")
    total_rows_ingested: int = Field(..., description="Total rows ingested into Bronze across all tenants")
    total_batches: int = Field(..., description="Total batches processed")
    active_tenants_count: int = Field(..., description="Number of tenants with recorded pipeline activity")
    pipeline_runs_per_day: List[DailyPipelineRunUsage] = Field(
        default_factory=list,
        description="Daily pipeline execution volume trend",
    )
    batches_per_tenant: List[TenantBatchUsage] = Field(
        default_factory=list,
        description="Batch volume distribution by tenant",
    )
    total_rows_ingested_over_time: List[DailyRowsIngestedUsage] = Field(
        default_factory=list,
        description="Daily row volume ingestion trend",
    )
