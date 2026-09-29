import api from './api';
import {
  PlatformUsageResponse,
  TenantCompareRequest,
  TenantCompareResponse,
  TenantDashboardViewAs,
  TenantHealthListResponse,
} from '@/types/oversight';

export const oversightService = {
  /**
   * Admin "View-As": fetch full Gold dashboard data for any specific tenant
   */
  async getTenantDashboard(
    tenantId: number | string,
    days?: number
  ): Promise<TenantDashboardViewAs> {
    const params = days ? { days } : {};
    const response = await api.get<TenantDashboardViewAs>(
      `/oversight/dashboard/${tenantId}`,
      { params }
    );
    return response.data;
  },

  /**
   * Fetch system-wide tenant health scores and breakdown
   */
  async getTenantHealth(): Promise<TenantHealthListResponse> {
    const response = await api.get<TenantHealthListResponse>('/oversight/tenant-health');
    return response.data;
  },

  /**
   * Multi-tenant side-by-side performance comparison
   */
  async compareTenants(
    payload: TenantCompareRequest
  ): Promise<TenantCompareResponse> {
    const response = await api.post<TenantCompareResponse>(
      '/oversight/compare',
      payload
    );
    return response.data;
  },

  /**
   * Fetch platform usage trends (pipeline runs, row volumes, tenant batches)
   */
  async getPlatformUsage(): Promise<PlatformUsageResponse> {
    const response = await api.get<PlatformUsageResponse>('/oversight/usage');
    return response.data;
  },

  /**
   * Download the complete system ETL audit log as CSV
   */
  async downloadAuditExport(startDate?: string, endDate?: string): Promise<void> {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await api.get('/oversight/audit-export', {
      params,
      responseType: 'blob',
    });

    // Create a temporary link element and trigger download
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().split('T')[0];
    link.setAttribute('download', `helios_audit_export_${timestamp}.csv`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
