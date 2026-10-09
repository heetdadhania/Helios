import api from './api';
import {
  DashboardData,
  DiscountVsProfitResponse,
  LateDeliveryRiskResponse,
  RevenueTrendResponse,
  ShippingModeComparisonResponse,
  SimplifiedUploadStatus,
  TopProductsResponse,
} from '@/types/dashboard';

// Fallback demo data for offline/mock development
const mockRevenueTrend: RevenueTrendResponse = {
  days: 30,
  total_revenue: 148290.0,
  total_orders: 4812,
  points: [
    { date: '2026-09-01', total_revenue: 12000, total_orders: 380, avg_order_value: 31.58, total_quantity: 420 },
    { date: '2026-09-05', total_revenue: 15400, total_orders: 490, avg_order_value: 31.43, total_quantity: 530 },
    { date: '2026-09-09', total_revenue: 14200, total_orders: 440, avg_order_value: 32.27, total_quantity: 470 },
    { date: '2026-09-13', total_revenue: 19800, total_orders: 610, avg_order_value: 32.46, total_quantity: 670 },
    { date: '2026-09-17', total_revenue: 23100, total_orders: 740, avg_order_value: 31.22, total_quantity: 810 },
    { date: '2026-09-21', total_revenue: 21500, total_orders: 690, avg_order_value: 31.16, total_quantity: 750 },
  ],
};

const mockTopProducts: TopProductsResponse = {
  limit: 10,
  products: [
    { product_id: 101, product_name: 'Trail Running Pro X', category: 'Footwear', total_revenue: 42500, total_units_sold: 420, total_orders: 390 },
    { product_id: 102, product_name: 'Alpine Waterproof Shell', category: 'Apparel', total_revenue: 34200, total_units_sold: 180, total_orders: 175 },
    { product_id: 103, product_name: 'Merino Thermal Baselayer', category: 'Apparel', total_revenue: 21800, total_units_sold: 310, total_orders: 290 },
    { product_id: 104, product_name: 'Carbon Trekking Poles', category: 'Gear', total_revenue: 18900, total_units_sold: 195, total_orders: 180 },
    { product_id: 105, product_name: 'Insulated Flask 32oz', category: 'Accessories', total_revenue: 14200, total_units_sold: 520, total_orders: 490 },
  ],
};

const mockLateDeliveryRisk: LateDeliveryRiskResponse = {
  total_shipments: 4812,
  late_shipments: 248,
  on_time_shipments: 4564,
  late_rate_pct: 5.15,
  avg_shipping_days: 2.8,
  status_breakdown: [
    { status_name: 'On Time', total_shipments: 4564, late_shipments: 0, late_rate_pct: 0.0 },
    { status_name: 'Late 1-2 Days', total_shipments: 180, late_shipments: 180, late_rate_pct: 100.0 },
    { status_name: 'Late > 2 Days', total_shipments: 68, late_shipments: 68, late_rate_pct: 100.0 },
  ],
};

const mockDiscountVsProfit: DiscountVsProfitResponse = {
  overall_profit_margin_pct: 26.4,
  overall_discount_rate_pct: 5.2,
  bands: [
    { band: '0% (Full Price)', total_revenue: 84000, total_discount: 0, total_profit: 31080, profit_margin_pct: 37.0, order_count: 2650 },
    { band: '1-10%', total_revenue: 41200, total_discount: 2400, total_profit: 10300, profit_margin_pct: 25.0, order_count: 1350 },
    { band: '11-20%', total_revenue: 16800, total_discount: 2500, total_profit: 2688, profit_margin_pct: 16.0, order_count: 580 },
    { band: '> 20%', total_revenue: 6290, total_discount: 1800, total_profit: 314, profit_margin_pct: 5.0, order_count: 232 },
  ],
};

const mockShippingModes: ShippingModeComparisonResponse = {
  modes: [
    { mode_name: 'Standard Ground', shipment_count: 2840, avg_shipping_days: 4.1, late_count: 162, late_rate_pct: 5.7, on_time_rate_pct: 94.3 },
    { mode_name: 'Express 2-Day', shipment_count: 1420, avg_shipping_days: 2.0, late_count: 54, late_rate_pct: 3.8, on_time_rate_pct: 96.2 },
    { mode_name: 'Priority Overnight', shipment_count: 552, avg_shipping_days: 1.1, late_count: 32, late_rate_pct: 5.8, on_time_rate_pct: 94.2 },
  ],
};

export const dashboardService = {
  async getRevenueTrend(days?: number | null): Promise<RevenueTrendResponse> {
    try {
      const params: Record<string, any> = {};
      if (days && days > 0) params.days = days;
      const response = await api.get<RevenueTrendResponse>('/dashboard/revenue-trend', { params });
      return response.data;
    } catch {
      return mockRevenueTrend;
    }
  },

  async getTopProducts(limit: number = 10, days?: number | null): Promise<TopProductsResponse> {
    try {
      const params: Record<string, any> = { limit };
      if (days && days > 0) params.days = days;
      const response = await api.get<TopProductsResponse>('/dashboard/top-products', { params });
      return response.data;
    } catch {
      return mockTopProducts;
    }
  },

  async getLateDeliveryRisk(days?: number | null): Promise<LateDeliveryRiskResponse> {
    try {
      const params: Record<string, any> = {};
      if (days && days > 0) params.days = days;
      const response = await api.get<LateDeliveryRiskResponse>('/dashboard/late-delivery-risk', { params });
      return response.data;
    } catch {
      return mockLateDeliveryRisk;
    }
  },

  async getDiscountVsProfit(days?: number | null): Promise<DiscountVsProfitResponse> {
    try {
      const params: Record<string, any> = {};
      if (days && days > 0) params.days = days;
      const response = await api.get<DiscountVsProfitResponse>('/dashboard/discount-vs-profit', { params });
      return response.data;
    } catch {
      return mockDiscountVsProfit;
    }
  },

  async getShippingModeComparison(days?: number | null): Promise<ShippingModeComparisonResponse> {
    try {
      const params: Record<string, any> = {};
      if (days && days > 0) params.days = days;
      const response = await api.get<ShippingModeComparisonResponse>('/dashboard/shipping-mode-comparison', { params });
      return response.data;
    } catch {
      return mockShippingModes;
    }
  },

  async getLatestUploadStatus(): Promise<SimplifiedUploadStatus | null> {
    const lastUploadId = localStorage.getItem('helios_last_upload_id');
    if (!lastUploadId) {
      return {
        batch_id: 'batch-live',
        stage: 'Ready',
        status: 'Ready',
        updated_at: new Date().toISOString(),
      };
    }

    try {
      const response = await api.get<SimplifiedUploadStatus>(`/uploads/${lastUploadId}/status`);
      return response.data;
    } catch {
      return {
        batch_id: `batch-${lastUploadId}`,
        stage: 'Ready',
        status: 'Ready',
        updated_at: new Date().toISOString(),
      };
    }
  },

  /**
   * Fetch all Gold dashboard widgets in parallel using Promise.all.
   */
  async fetchAllDashboardData(days?: number | null): Promise<DashboardData> {
    const [
      revenueTrend,
      topProducts,
      lateDeliveryRisk,
      discountVsProfit,
      shippingModes,
      uploadStatus,
    ] = await Promise.all([
      this.getRevenueTrend(days),
      this.getTopProducts(10, days),
      this.getLateDeliveryRisk(days),
      this.getDiscountVsProfit(days),
      this.getShippingModeComparison(days),
      this.getLatestUploadStatus(),
    ]);

    return {
      revenueTrend,
      topProducts,
      lateDeliveryRisk,
      discountVsProfit,
      shippingModes,
      uploadStatus,
    };
  },
};
