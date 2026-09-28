import api from './api';
import {
  AdminHistoryItem,
  HistoryFilterParams,
  SmbHistoryItem,
  TeamHistoryItem,
} from '@/types/history';

export const historyService = {
  /**
   * Fetch caller's tenant submission history (SMB Owner).
   */
  async getMyHistory(): Promise<SmbHistoryItem[]> {
    try {
      const response = await api.get<SmbHistoryItem[]>('/history/mine');
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return [
          {
            batch_id: 'batch-demo-1',
            date: new Date(Date.now() - 1000 * 60 * 30).toLocaleString(),
            status: 'Ready',
            label: 'Data received',
          },
          {
            batch_id: 'batch-demo-2',
            date: new Date(Date.now() - 1000 * 60 * 60 * 3).toLocaleString(),
            status: 'Processing',
            label: 'Data received',
          },
          {
            batch_id: 'batch-demo-3',
            date: new Date(Date.now() - 1000 * 60 * 60 * 24).toLocaleString(),
            status: 'Needs attention — please resend',
            label: 'Data received',
          },
        ];
      }
      throw error;
    }
  },

  /**
   * Fetch operational submission history for Team Members / Admins.
   */
  async getTeamHistory(filters?: HistoryFilterParams): Promise<TeamHistoryItem[]> {
    try {
      const params: Record<string, string> = {};
      if (filters?.status && filters.status !== 'all') {
        params.status = filters.status;
      }
      if (filters?.tenant && filters.tenant.trim()) {
        params.tenant = filters.tenant.trim();
      }
      const response = await api.get<TeamHistoryItem[]>('/history/team', { params });
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return [
          {
            batch_id: 'batch-tm-101',
            tenant_id: 1,
            tenant: 'Summit Athletics',
            source_type: 'upload',
            stage: 'gold_transform',
            status: 'success',
            error_message: null,
            timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          },
          {
            batch_id: 'batch-tm-102',
            tenant_id: 2,
            tenant: 'Nordic Outfitters',
            source_type: 'db_connection',
            stage: 'silver_clean',
            status: 'failed',
            error_message: 'ColumnFormatMismatch: Expected numeric timestamp in col 3',
            timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          },
          {
            batch_id: 'batch-tm-103',
            tenant_id: 1,
            tenant: 'Summit Athletics',
            source_type: 'api_push',
            stage: 'silver_clean',
            status: 'silver_running',
            error_message: null,
            timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          },
        ];
      }
      throw error;
    }
  },

  /**
   * Fetch system-wide submission history with Handled By column (Admin).
   */
  async getAdminHistory(filters?: HistoryFilterParams): Promise<AdminHistoryItem[]> {
    try {
      const params: Record<string, string> = {};
      if (filters?.status && filters.status !== 'all') {
        params.status = filters.status;
      }
      if (filters?.tenant && filters.tenant.trim()) {
        params.tenant = filters.tenant.trim();
      }
      const response = await api.get<AdminHistoryItem[]>('/history/admin', { params });
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return [
          {
            batch_id: 'batch-adm-201',
            tenant_id: 1,
            tenant: 'Summit Athletics',
            source_type: 'upload',
            stage: 'gold_transform',
            status: 'success',
            error_message: null,
            timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
            handled_by: 'Alice Support',
          },
          {
            batch_id: 'batch-adm-202',
            tenant_id: 2,
            tenant: 'Nordic Outfitters',
            source_type: 'db_connection',
            stage: 'silver_clean',
            status: 'failed',
            error_message: 'ColumnFormatMismatch: Expected numeric timestamp in col 3',
            timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
            handled_by: 'N/A',
          },
          {
            batch_id: 'batch-adm-203',
            tenant_id: 3,
            tenant: 'Bluebird Home Decor',
            source_type: 'upload',
            stage: 'schema_inference',
            status: 'awaiting_confirmation',
            error_message: null,
            timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
            handled_by: 'Charlie Specialist',
          },
        ];
      }
      throw error;
    }
  },
};
