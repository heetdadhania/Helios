import api from './api';
import {
  AdminHistoryItem,
  HistoryFilterParams,
  SmbHistoryItem,
  TeamHistoryItem,
} from '@/types/history';
import { PaginatedResponse } from '@/types/pagination';

export const historyService = {
  /**
   * Fetch caller's tenant submission history (SMB Owner) with server-side pagination.
   */
  async getMyHistory(
    page: number = 1,
    pageSize: number = 20,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
  ): Promise<PaginatedResponse<SmbHistoryItem>> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (sortBy && sortBy.trim()) params.sort_by = sortBy.trim();
    if (sortOrder) params.sort_order = sortOrder;
    const response = await api.get<PaginatedResponse<SmbHistoryItem>>('/history/mine', {
      params,
    });
    return response.data;
  },

  /**
   * Fetch operational submission history for Team Members / Admins with server-side pagination.
   */
  async getTeamHistory(
    filters?: HistoryFilterParams,
    page: number = 1,
    pageSize: number = 20,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
  ): Promise<PaginatedResponse<TeamHistoryItem>> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (filters?.status && filters.status !== 'all') {
      params.status = filters.status;
    }
    if (filters?.tenant && filters.tenant.trim()) {
      params.tenant = filters.tenant.trim();
    }
    if (sortBy && sortBy.trim()) params.sort_by = sortBy.trim();
    if (sortOrder) params.sort_order = sortOrder;
    const response = await api.get<PaginatedResponse<TeamHistoryItem>>('/history/team', { params });
    return response.data;
  },

  /**
   * Fetch system-wide submission history with Handled By column (Admin) with server-side pagination.
   */
  async getAdminHistory(
    filters?: HistoryFilterParams,
    page: number = 1,
    pageSize: number = 20,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
  ): Promise<PaginatedResponse<AdminHistoryItem>> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (filters?.status && filters.status !== 'all') {
      params.status = filters.status;
    }
    if (filters?.tenant && filters.tenant.trim()) {
      params.tenant = filters.tenant.trim();
    }
    if (sortBy && sortBy.trim()) params.sort_by = sortBy.trim();
    if (sortOrder) params.sort_order = sortOrder;
    const response = await api.get<PaginatedResponse<AdminHistoryItem>>('/history/admin', { params });
    return response.data;
  },
};
