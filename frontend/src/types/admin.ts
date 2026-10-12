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
  target_field: string | null;
  target_column?: string;
  inferred_type: string;
  similarity_score: number;
  confidence_score: number;
  is_exact: boolean;
  is_nullable?: boolean;
}

export interface SchemaPreview {
  batch_id: string;
  tenant_id: string;
  tenant_name?: string;
  source_type: SourceType;
  inferred_template?: string;
  detected_template?: string;
  confidence_score: number;
  suggested_silver_table?: string;
  column_mappings: ColumnMapping[];
  sample_rows: Record<string, any>[];
  internal_notes?: string | null;
  unmapped_required_fields?: string[];
}

export interface ConfirmSchemaPayload {
  column_mappings: Record<string, string>;
  silver_table?: string;
  notes?: string;
  internal_notes?: string;
  confirmed_template?: string;
}

export interface BatchCompleteness {
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  completeness_percentage: number;
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

  business_name?: string;
  industry?: string;
  contact_person_name?: string;
  contact_email?: string;
  phone_number?: string;
  address_line1?: string;
  address_line2?: string | null;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  website_url?: string | null;
  tax_id?: string | null;
  assigned_team_member_id?: number | null;
  temporary_password?: string | null;
  owner_email?: string | null;
}

export interface CreateTenantPayload {
  business_name: string;
  industry: string;
  contact_person_name: string;
  contact_email: string;
  phone_number: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  website_url?: string | null;
  tax_id?: string | null;
  assigned_team_member_id?: number | null;
  owner_email?: string | null;

  // Optional display fields
  name?: string;
  slug?: string;
  catalog_name?: string;
  schema_name?: string;
  tier?: 'Starter' | 'Growth' | 'Enterprise';
}

export interface TeamMember {
  user_id: string | number;
  id?: string | number;
  name: string;
  email: string;
  phone_number?: string;
  role: 'admin' | 'team_member';
  staff_id?: string | null;
  designation?: string | null;
  is_active: boolean;
  created_at: string;
  tenant_ids?: number[];
  assigned_tenants: string[];
  must_change_password?: boolean;
}

export interface CreateTeamMemberPayload {
  name: string;
  email: string;
  phone_number: string;
  role: 'admin' | 'team_member';
  staff_id?: string;
  designation?: string;
  tenant_ids?: number[];
  assigned_tenants?: string[];
}

export interface CreateTeamMemberResponse extends TeamMember {
  temporary_password?: string;
}

export interface AssignTenantPayload {
  user_id: string | number;
  tenant_id: string | number;
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
