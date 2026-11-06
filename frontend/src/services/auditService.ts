import api from './api';
import { AuditLogItem, AuditTrailFilters } from '@/types/audit';
import { PaginatedResponse } from '@/types/pagination';

export const auditService = {
  async getAuditTrail(
    filters?: AuditTrailFilters,
    page: number = 1,
    pageSize: number = 20,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
  ): Promise<PaginatedResponse<AuditLogItem>> {
    const params: Record<string, any> = {
      page,
      page_size: pageSize,
    };
    if (filters?.start_date) params.start_date = filters.start_date;
    if (filters?.end_date) params.end_date = filters.end_date;
    if (filters?.actor) params.actor = filters.actor;
    if (filters?.action && filters.action !== 'all') params.action = filters.action;
    if (filters?.organization && filters.organization !== 'all') params.organization = filters.organization;
    if (filters?.tenant_id && filters.tenant_id !== 'all') params.tenant_id = filters.tenant_id;
    if (sortBy && sortBy.trim()) params.sort_by = sortBy.trim();
    if (sortOrder) params.sort_order = sortOrder;

    const response = await api.get<PaginatedResponse<AuditLogItem>>('/audit', { params });
    return response.data;
  },
};

