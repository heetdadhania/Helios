import api from './api';
import {
  PipelineRun,
  PipelineRunDetail,
  RetryRequest,
  RetryResponse,
  RestartResponse,
} from '@/types/pipelineHealth';

const PIPELINE_BASE = '/pipeline';

export const pipelineHealthService = {
  /**
   * Retrieve list of pipeline execution runs.
   * Team Members see assigned tenants; Admins see all.
   */
  async listRuns(status?: string): Promise<PipelineRun[]> {
    const params = status && status !== 'all' ? { status } : {};
    const response = await api.get<PipelineRun[]>(`${PIPELINE_BASE}/runs`, { params });
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

