export interface SupportMessage {
  message_id: number;
  tenant_id: number;
  tenant_name?: string | null;
  from_user_id: number;
  from_user_name?: string | null;
  to_user_id: number;
  to_user_name?: string | null;
  message: string;
  status: 'open' | 'resolved';
  created_at: string;
  resolved_at?: string | null;
}

export interface SupportMessageCreatePayload {
  message: string;
}

export interface SupportMessageResolveResponse {
  success: boolean;
  message: string;
  message_id: number;
  status: string;
  resolved_at: string;
}
