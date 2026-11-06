import api from './api';
import {
  PipelineRun,
  PipelineRunDetail,
  RetryRequest,
  RetryResponse,
  RestartResponse,
} from '@/types/pipelineHealth';
import { PaginatedResponse } from '@/types/pagination';

const PIPELINE_BASE = '/pipeline';

export const pipelineHealthService = {
  /**
   * Retrieve list of pipeline execution runs with server-side pagination.
   * Team Members see assigned tenants; Admins see all.
   */
  async listRuns(
    status?: string,
    tenantId?: string,
    page: number = 1,
    pageSize: number = 20,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
  ): Promise<PaginatedResponse<PipelineRun>> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (status && status !== 'all') {
      params.status = status;
    }
    if (tenantId && tenantId !== 'all') {
      params.tenant_id = tenantId;
    }
    if (sortBy && sortBy.trim()) {
      params.sort_by = sortBy.trim();
    }
    if (sortOrder) {
      params.sort_order = sortOrder;
    }
    const response = await api.get<PaginatedResponse<PipelineRun>>(`${PIPELINE_BASE}/runs`, { params });
    return response.data;
  },

  /**
   * Fetch full run detail including stage progression and audit log items.
   */
  async getRunDetail(batchId: string): Promise<PipelineRunDetail> {
    const response = await api.get<PipelineRunDetail>(`${PIPELINE_BASE}/runs/${batchId}`);
    return response.data;
  },

  /**
   * Trigger Databricks Jobs repair-run on only the failed task and downstream dependencies.
   * Reuses earlier stage data (e.g. Bronze data is preserved and untouched).
   */
  async retryFailedStage(batchId: string, request?: RetryRequest): Promise<RetryResponse> {
    const response = await api.post<RetryResponse>(
      `${PIPELINE_BASE}/runs/${batchId}/retry-failed-stage`,
      request || {}
    );
    return response.data;
  },

  /**
   * Mark batch as restart_required and dispatch SMB Owner re-upload notification.
   * Does NOT re-run the existing batch in place.
   */
  async fullRestart(batchId: string): Promise<RestartResponse> {
    const response = await api.post<RestartResponse>(
      `${PIPELINE_BASE}/runs/${batchId}/full-restart`
    );
    return response.data;
  },

  /**
   * Cancel an actively running pipeline batch.
   */
  async cancelRun(batchId: string): Promise<any> {
    const response = await api.post(`${PIPELINE_BASE}/runs/${batchId}/cancel`);
    return response.data;
  },
};

