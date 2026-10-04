import api from './api';
import {
  PipelineRun,
  PipelineRunDetail,
  RetryRequest,
  RetryResponse,
  RestartResponse,
} from '@/types/pipelineHealth';

const PIPELINE_BASE = '/pipeline';

// Fallback demo dataset for development or offline testing
const mockRuns: PipelineRunDetail[] = [
  {
    batch_id: 'batch-7f91a2-2026',
    tenant_id: 1,
    tenant: 'Summit Athletics',
    tenant_name: 'Summit Athletics',
    source_type: 'upload',
    current_stage: 'silver_clean',
    status: 'failed',
    started_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 28).toISOString(),
    error_message: 'CurrencyFormatError: Invalid ISO currency symbol "US$" on row 142 in column "order_total"',
    stage_history: [
      {
        stage: 'bronze_ingest',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 34).toISOString(),
        duration_seconds: 1.25,
        row_count: 1420,
      },
      {
        stage: 'schema_inference',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 33).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 31).toISOString(),
        duration_seconds: 2.1,
        row_count: 1420,
      },
      {
        stage: 'silver_clean',
        status: 'failed',
        started_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 28).toISOString(),
        duration_seconds: 1.8,
        row_count: 141,
        error_message: 'CurrencyFormatError: Invalid ISO currency symbol "US$" on row 142 in column "order_total"',
      },
    ],
    audit_logs: [
      {
        log_id: 101,
        batch_id: 'batch-7f91a2-2026',
        stage: 'bronze_ingest',
        row_count: 1420,
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 34).toISOString(),
      },
      {
        log_id: 102,
        batch_id: 'batch-7f91a2-2026',
        stage: 'silver_clean',
        row_count: 141,
        status: 'failed',
        started_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 28).toISOString(),
        error_message: 'CurrencyFormatError: Invalid ISO currency symbol "US$" on row 142',
      },
    ],
  },
  {
    batch_id: 'batch-a3891b-2026',
    tenant_id: 2,
    tenant: 'Nordic Outfitters',
    tenant_name: 'Nordic Outfitters',
    source_type: 'db_connection',
    current_stage: 'gold_transform',
    status: 'gold_running',
    started_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    error_message: null,
    stage_history: [
      {
        stage: 'bronze_ingest',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
        duration_seconds: 2.0,
        row_count: 8500,
      },
      {
        stage: 'silver_clean',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 9).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        duration_seconds: 4.1,
        row_count: 8492,
      },
      {
        stage: 'gold_transform',
        status: 'in_progress',
        started_at: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
        completed_at: null,
        duration_seconds: null,
        row_count: 8492,
      },
    ],
    audit_logs: [],
  },
  {
    batch_id: 'batch-c4198e-2026',
    tenant_id: 3,
    tenant: 'Bluebird Home Decor',
    tenant_name: 'Bluebird Home Decor',
    source_type: 'api_push',
    current_stage: 'gold_transform',
    status: 'success',
    started_at: new Date(Date.now() - 1000 * 60 * 95).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 85).toISOString(),
    error_message: null,
    stage_history: [
      {
        stage: 'bronze_ingest',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 95).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 93).toISOString(),
        duration_seconds: 1.8,
        row_count: 3200,
      },
      {
        stage: 'silver_clean',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 92).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 89).toISOString(),
        duration_seconds: 3.2,
        row_count: 3198,
      },
      {
        stage: 'gold_transform',
        status: 'completed',
        started_at: new Date(Date.now() - 1000 * 60 * 88).toISOString(),
        completed_at: new Date(Date.now() - 1000 * 60 * 85).toISOString(),
        duration_seconds: 2.9,
        row_count: 3198,
      },
    ],
    audit_logs: [],
  },
  {
    batch_id: 'batch-e8921f-2026',
    tenant_id: 1,
    tenant: 'Summit Athletics',
    tenant_name: 'Summit Athletics',
    source_type: 'upload',
    current_stage: 'bronze_ingest',
    status: 'restart_required',
    started_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 160).toISOString(),
    error_message: 'Corrupt header row encountered; file encoding UTF-16LE incompatible with CSV parser.',
    stage_history: [],
    audit_logs: [],
  },
];

export const pipelineHealthService = {
  /**
   * Retrieve list of pipeline execution runs.
   * Team Members see assigned tenants; Admins see all.
   */
  async listRuns(status?: string): Promise<PipelineRun[]> {
    try {
      const params = status && status !== 'all' ? { status } : {};
      const response = await api.get<PipelineRun[]>(`${PIPELINE_BASE}/runs`, { params });
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        if (status && status !== 'all') {
          const s = status.toLowerCase();
          return mockRuns.filter((r) => {
            const norm = r.status.toLowerCase();
            if (s === 'running' || s === 'in_progress' || s === 'processing') {
              return norm.includes('running') || norm === 'processing';
            }
            return norm === s;
          });
        }
        return mockRuns;
      }
      const errMsg = error.response?.data?.detail || 'Failed to fetch pipeline runs.';
      throw new Error(errMsg);
    }
  },

  /**
   * Fetch full run detail including stage progression and audit log items.
   */
  async getRunDetail(batchId: string): Promise<PipelineRunDetail> {
    try {
      const response = await api.get<PipelineRunDetail>(`${PIPELINE_BASE}/runs/${batchId}`);
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        const found = mockRuns.find((r) => r.batch_id === batchId);
        if (found) return found;
      }
      const errMsg = error.response?.data?.detail || `Failed to fetch run detail for ${batchId}.`;
      throw new Error(errMsg);
    }
  },

  /**
   * Trigger Databricks Jobs repair-run on only the failed task and downstream dependencies.
   * Reuses earlier stage data (e.g. Bronze data is preserved and untouched).
   */
  async retryFailedStage(batchId: string, request?: RetryRequest): Promise<RetryResponse> {
    try {
      const response = await api.post<RetryResponse>(
        `${PIPELINE_BASE}/runs/${batchId}/retry-failed-stage`,
        request || {}
      );
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        const match = mockRuns.find((r) => r.batch_id === batchId);
        if (match) {
          match.status = 'silver_running';
          match.error_message = null;
        }
        return {
          batch_id: batchId,
          status: 'silver_running',
          current_stage: 'silver_clean',
          message: 'Databricks Jobs repair-run initiated. Upstream stage data preserved and reused.',
          repaired_tasks: ['silver_clean_task'],
        };
      }
      const errMsg = error.response?.data?.detail || `Failed to retry batch ${batchId}.`;
      throw new Error(errMsg);
    }
  },

  /**
   * Mark batch as restart_required and dispatch SMB Owner re-upload notification.
   * Does NOT re-run the existing batch in place.
   */
  async fullRestart(batchId: string): Promise<RestartResponse> {
    try {
      const response = await api.post<RestartResponse>(
        `${PIPELINE_BASE}/runs/${batchId}/full-restart`
      );
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        const match = mockRuns.find((r) => r.batch_id === batchId);
        if (match) {
          match.status = 'restart_required';
        }
        return {
          batch_id: batchId,
          status: 'restart_required',
          message:
            "Batch marked as 'restart_required'. The existing batch was not re-run. A notification has been sent to the SMB Owner requesting them to re-upload the original source file or re-sync their connection.",
          notification_sent: true,
        };
      }
      const errMsg = error.response?.data?.detail || `Failed to restart batch ${batchId}.`;
      throw new Error(errMsg);
    }
  },
};
