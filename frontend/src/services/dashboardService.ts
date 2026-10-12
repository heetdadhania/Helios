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

export const dashboardService = {
  async getRevenueTrend(days?: number | null): Promise<RevenueTrendResponse> {
    const params: Record<string, any> = {};
    if (days && days > 0) params.days = days;
    const response = await api.get<RevenueTrendResponse>('/dashboard/revenue-trend', { params });
    return response.data;
  },

  async getTopProducts(limit: number = 10, days?: number | null): Promise<TopProductsResponse> {
    const params: Record<string, any> = { limit };
    if (days && days > 0) params.days = days;
    const response = await api.get<TopProductsResponse>('/dashboard/top-products', { params });
    return response.data;
  },

  async getLateDeliveryRisk(days?: number | null): Promise<LateDeliveryRiskResponse> {
    const params: Record<string, any> = {};
    if (days && days > 0) params.days = days;
    const response = await api.get<LateDeliveryRiskResponse>('/dashboard/late-delivery-risk', { params });
    return response.data;
  },

  async getDiscountVsProfit(days?: number | null): Promise<DiscountVsProfitResponse> {
    const params: Record<string, any> = {};
    if (days && days > 0) params.days = days;
    const response = await api.get<DiscountVsProfitResponse>('/dashboard/discount-vs-profit', { params });
    return response.data;
  },

  async getShippingModeComparison(days?: number | null): Promise<ShippingModeComparisonResponse> {
    const params: Record<string, any> = {};
    if (days && days > 0) params.days = days;
    const response = await api.get<ShippingModeComparisonResponse>('/dashboard/shipping-mode-comparison', { params });
    return response.data;
  },

  async getLatestUploadStatus(): Promise<SimplifiedUploadStatus | null> {
    const lastUploadId = localStorage.getItem('helios_last_upload_id');
    if (!lastUploadId) {
      return null;
    }

    try {
      const response = await api.get<SimplifiedUploadStatus>(`/uploads/${lastUploadId}/status`);
      return response.data;
    } catch (err: any) {
      if (err?.response?.status === 404) {
        return null;
      }
      throw err;
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
