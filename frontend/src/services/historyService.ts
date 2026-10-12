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
    const response = await api.get<SmbHistoryItem[]>('/history/mine');
    return response.data;
  },

  /**
   * Fetch operational submission history for Team Members / Admins.
   */
  async getTeamHistory(filters?: HistoryFilterParams): Promise<TeamHistoryItem[]> {
    const params: Record<string, string> = {};
    if (filters?.status && filters.status !== 'all') {
      params.status = filters.status;
    }
    if (filters?.tenant && filters.tenant.trim()) {
      params.tenant = filters.tenant.trim();
    }
    const response = await api.get<TeamHistoryItem[]>('/history/team', { params });
    return response.data;
  },

  /**
   * Fetch system-wide submission history with Handled By column (Admin).
   */
  async getAdminHistory(filters?: HistoryFilterParams): Promise<AdminHistoryItem[]> {
    const params: Record<string, string> = {};
    if (filters?.status && filters.status !== 'all') {
      params.status = filters.status;
    }
    if (filters?.tenant && filters.tenant.trim()) {
      params.tenant = filters.tenant.trim();
    }
    const response = await api.get<AdminHistoryItem[]>('/history/admin', { params });
    return response.data;
  },
};
