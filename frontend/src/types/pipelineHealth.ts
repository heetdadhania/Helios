export type IngestionSourceType = 'upload' | 'db_connection' | 'api_push' | string;

export type PipelineStage =
  | 'bronze_ingest'
  | 'bronze'
  | 'schema_inference'
  | 'awaiting_confirmation'
  | 'silver_clean'
  | 'silver'
  | 'gold_transform'
  | 'gold'
  | string;

export type PipelineRunStatus =
  | 'ingested'
  | 'schema_inference_running'
  | 'awaiting_confirmation'
  | 'silver_running'
  | 'gold_running'
  | 'success'
  | 'failed'
  | 'restart_required'
  | string;

export interface PipelineRun {
  batch_id: string;
  tenant_id: number;
  tenant?: string | null;
  tenant_name?: string | null;
  source_type: IngestionSourceType;
  current_stage: PipelineStage;
  status: PipelineRunStatus;
  started_at?: string | null;
  updated_at?: string | null;
  error_message?: string | null;
}

export interface EtlAuditLog {
  log_id?: number | null;
  batch_id: string;
  stage: string;
  row_count?: number | null;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface StageHistoryItem {
  stage: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  row_count?: number | null;
  error_message?: string | null;
}

export interface PipelineRunDetail extends PipelineRun {
  stage_history: StageHistoryItem[];
  audit_logs: EtlAuditLog[];
}

export interface RetryRequest {
  rerun_tasks?: string[];
  reason?: string;
}

export interface RetryResponse {
  batch_id: string;
  status: string;
  current_stage: string;
  message: string;
  repaired_tasks?: string[] | null;
}

export interface RestartResponse {
  batch_id: string;
  status: string;
  message: string;
  notification_sent: boolean;
}
