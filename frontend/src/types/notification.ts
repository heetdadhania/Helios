export type NotificationType =
  | 'info'
  | 'warning'
  | 'error'
  | 'approval_required'
  | 'pipeline_success'
  | 'upload_received'
  | 'pipeline_failed'
  | 'dashboard_ready'
  | 'restart_required';

export interface Notification {
  notification_id: number;
  tenant_id?: number | null;
  user_id?: number | null;
  message: string;
  type: NotificationType | string;
  is_read: boolean;
  created_at?: string | null;
}

export interface NotificationReadResponse {
  notification_id: number;
  is_read: boolean;
  message: string;
}

export interface NotificationFilterParams {
  unread_only?: boolean;
  limit?: number;
  offset?: number;
}
