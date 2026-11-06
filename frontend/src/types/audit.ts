export interface AuditLogItem {
  audit_id: number;
  occurred_at: string;
  actor_user_id?: number | null;
  actor_name?: string | null;
  actor_email?: string | null;
  actor_role?: string | null;
  action: string;
  tenant_id?: number | null;
  tenant_name?: string | null;
  batch_id?: string | null;
  reason?: string | null;
  details_json?: string | null;
}

export interface AuditTrailFilters {
  start_date?: string;
  end_date?: string;
  actor?: string;
  action?: string;
  tenant_id?: number | string;
  organization?: string;
}

