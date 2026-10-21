export interface AdminHomeSummary {
  organizations_active: number;
  organizations_inactive: number;
  organizations_total: number;
  organization_owners_active: number;
  team_members: number;
  pending_uploads: number;
  running_pipelines: number;
  failed_pipelines: number;
  open_support_messages: number;
}

export interface RevenueByOrganizationItem {
  tenant_id: number;
  organization_name: string;
  total_revenue: number;
}

export interface DailyPipelineRunStatus {
  date: string;
  successful_runs: number;
  failed_runs: number;
  total_runs: number;
}

export interface AdminHomeCharts {
  revenue_by_organization: RevenueByOrganizationItem[];
  pipeline_runs_per_day: DailyPipelineRunStatus[];
}

export interface OrganizationTableRow {
  tenant_id: number;
  name: string;
  owner: string;
  assigned_team_member: string;
  last_data_received?: string | null;
  is_active: boolean;
}

export interface AdminHomeActivityItem {
  batch_id?: string | null;
  tenant_id?: number | null;
  tenant_name?: string | null;
  stage?: string | null;
  status: string;
  error_message?: string | null;
  timestamp?: string | null;
}

export interface AdminHomeTables {
  organizations: OrganizationTableRow[];
  recent_activity: AdminHomeActivityItem[];
}

export interface AdminHomeResponse {
  summary: AdminHomeSummary;
  charts: AdminHomeCharts;
  tables: AdminHomeTables;
}
