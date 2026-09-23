export type SourceType = 'upload' | 'db_connection' | 'api_push';

export interface PendingUpload {
  batch_id: string;
  tenant_id: string;
  tenant_name?: string;
  source_type: SourceType;
  filename: string;
  file_size_bytes?: number;
  row_count: number;
  status: string;
  created_at: string;
}

export interface ColumnMapping {
  source_column: string;
  target_column: string;
  inferred_type: string;
  confidence_score: number;
  is_nullable: boolean;
}

export interface SchemaPreview {
  batch_id: string;
  tenant_id: string;
  tenant_name?: string;
  source_type: SourceType;
  inferred_template: string;
  confidence_score: number;
  suggested_silver_table: string;
  column_mappings: ColumnMapping[];
  sample_rows: Record<string, any>[];
}

export interface ConfirmSchemaPayload {
  column_mappings: Record<string, string>;
  silver_table?: string;
  notes?: string;
}

export interface ConfirmSchemaResponse {
  batch_id: string;
  silver_job_run_id: string;
  status: string;
  confirmed_at: string;
}

export interface Tenant {
  tenant_id: string;
  name: string;
  slug: string;
  catalog_name: string;
  schema_name: string;
  tier: 'Starter' | 'Growth' | 'Enterprise';
  is_active: boolean;
  created_at: string;
  active_pipelines?: number;
}

export interface CreateTenantPayload {
  name: string;
  slug: string;
  catalog_name?: string;
  schema_name?: string;
  tier?: 'Starter' | 'Growth' | 'Enterprise';
}

export interface TeamMember {
  user_id: string;
  name: string;
  email: string;
  role: 'admin' | 'team_member';
  is_active: boolean;
  created_at: string;
  assigned_tenants: string[];
}

export interface CreateTeamMemberPayload {
  name: string;
  email: string;
  role: 'admin' | 'team_member';
  assigned_tenants?: string[];
}

export interface AssignTenantPayload {
  user_id: string;
  tenant_id: string;
}

export interface DataQualityLogItem {
  id: string;
  batch_id: string;
  tenant_id: string;
  tenant_name: string;
  table_name: string;
  rejection_reason: string;
  timestamp: string;
  error_category?: 'Schema Drift' | 'Null Threshold Exceeded' | 'Type Mismatch' | 'Duplicate Key';
}
