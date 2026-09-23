export type SupportedDbType = 'mysql' | 'postgresql' | 'sqlserver';

export interface DbTypeOption {
  value: SupportedDbType;
  label: string;
  defaultPort: number;
  description: string;
}

export interface DbConnectionCreate {
  db_type: SupportedDbType;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  table_or_query: string;
  is_active?: boolean;
}

export interface DbConnectionOut {
  connection_id: number;
  tenant_id: number;
  db_type: SupportedDbType | string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  table_or_query: string;
  last_synced_at: string | null;
  created_at: string | null;
  is_active: boolean;
}

export interface DbConnectionTestResult {
  success: boolean;
  message: string;
}

export interface DbConnectionSyncResponse {
  upload_id: number;
  batch_id: string;
  status: string;
  connection_id?: number;
  rows_synced?: number;
  message?: string;
}

export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
}
