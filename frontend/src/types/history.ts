export interface SmbHistoryItem {
  batch_id: string;
  date: string;
  status: 'Ready' | 'Processing' | 'Needs attention — please resend' | string;
  label: string;
}

export interface TeamHistoryItem {
  batch_id: string;
  tenant_id: number;
  tenant: string;
  source_type: string;
  stage: string;
  status: string;
  error_message?: string | null;
  timestamp: string;
}

export interface AdminHistoryItem extends TeamHistoryItem {
  handled_by: string;
}

export interface HistoryFilterParams {
  status?: string;
  tenant?: string;
}
