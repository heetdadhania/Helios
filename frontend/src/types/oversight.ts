import {
  DiscountVsProfitResponse,
  LateDeliveryRiskResponse,
  RevenueTrendResponse,
  ShippingModeComparisonResponse,
  TopProductsResponse,
} from './dashboard';

// --- View-As Tenant Dashboard ---
export interface TenantDashboardViewAs {
  tenant_id: number;
  tenant_name: string;
  days: number | null;
  revenue_trend: RevenueTrendResponse;
  top_products: TopProductsResponse;
  late_delivery_risk: LateDeliveryRiskResponse;
  discount_vs_profit: DiscountVsProfitResponse;
  shipping_modes: ShippingModeComparisonResponse;
}

// --- Tenant Health ---
export type HealthStatusType = 'good' | 'needs_attention' | 'critical';

export interface TenantHealthItem {
  tenant_id: number;
  tenant_name: string;
  slug: string;
  tier: string;
  health_status: HealthStatusType;
  latest_pipeline_status: string | null;
  latest_batch_id: string | null;
  late_delivery_rate_pct: number;
  total_shipments: number;
  issues: string[];
  last_activity_at: string | null;
}

export interface TenantHealthListResponse {
  total_tenants: number;
  critical_count: number;
  needs_attention_count: number;
  good_count: number;
  tenants: TenantHealthItem[];
}

// --- Tenant Comparison ---
export interface TenantCompareRequest {
  tenant_ids: number[];
  days?: number | null;
}

export interface TenantComparisonMetric {
  tenant_id: number;
  tenant_name: string;
  tier: string;
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  total_shipments: number;
  late_delivery_pct: number;
  avg_shipping_days: number;
}

export interface TenantCompareResponse {
  days: number | null;
  compared_at: string;
  tenants: TenantComparisonMetric[];
}

// --- Platform Usage ---
export interface DailyPipelineRunUsage {
  date: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
}

export interface TenantBatchUsage {
  tenant_id: number;
  tenant_name: string;
  batch_count: number;
  last_batch_at: string | null;
}

export interface DailyRowsIngestedUsage {
  date: string;
  rows_ingested: number;
}

export interface PlatformUsageResponse {
  total_runs: number;
  total_rows_ingested: number;
  total_batches: number;
  active_tenants_count: number;
  pipeline_runs_per_day: DailyPipelineRunUsage[];
  batches_per_tenant: TenantBatchUsage[];
  total_rows_ingested_over_time: DailyRowsIngestedUsage[];
}
