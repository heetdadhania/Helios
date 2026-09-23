export interface RevenueTrendPoint {
  date: string;
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  total_quantity: number;
}

export interface RevenueTrendResponse {
  days: number;
  total_revenue: number;
  total_orders: number;
  points: RevenueTrendPoint[];
}

export interface TopProductItem {
  product_id: number;
  product_name: string;
  category: string | null;
  total_revenue: number;
  total_units_sold: number;
  total_orders: number;
}

export interface TopProductsResponse {
  limit: number;
  products: TopProductItem[];
}

export interface DeliveryRiskBreakdownItem {
  status_name: string;
  total_shipments: number;
  late_shipments: number;
  late_rate_pct: number;
}

export interface LateDeliveryRiskResponse {
  total_shipments: number;
  late_shipments: number;
  on_time_shipments: number;
  late_rate_pct: number;
  avg_shipping_days: number;
  status_breakdown: DeliveryRiskBreakdownItem[];
}

export interface DiscountProfitBand {
  band: string;
  total_revenue: number;
  total_discount: number;
  total_profit: number;
  profit_margin_pct: number;
  order_count: number;
}

export interface DiscountVsProfitResponse {
  overall_profit_margin_pct: number;
  overall_discount_rate_pct: number;
  bands: DiscountProfitBand[];
}

export interface ShippingModeComparisonItem {
  mode_name: string;
  shipment_count: number;
  avg_shipping_days: number;
  late_count: number;
  late_rate_pct: number;
  on_time_rate_pct: number;
}

export interface ShippingModeComparisonResponse {
  modes: ShippingModeComparisonItem[];
}

export interface SimplifiedUploadStatus {
  batch_id: string;
  stage: string; // Plain-language: "Processing", "Ready", "Failed"
  status: string; // Plain-language status description
  updated_at: string;
}

export interface DashboardData {
  revenueTrend: RevenueTrendResponse | null;
  topProducts: TopProductsResponse | null;
  lateDeliveryRisk: LateDeliveryRiskResponse | null;
  discountVsProfit: DiscountVsProfitResponse | null;
  shippingModes: ShippingModeComparisonResponse | null;
  uploadStatus: SimplifiedUploadStatus | null;
}
