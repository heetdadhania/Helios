export interface AssignedOrganization {
  tenant_id: number;
  business_name: string;
  last_data_date: string | null;
}

export interface PipelineCounts {
  pending_review: number;
  running: number;
  failed: number;
  stalled: number;
}

export interface OpenSupportMessage {
  message_id: number;
  tenant_id: number;
  tenant_name: string | null;
  from_user_id: number;
  from_user_name: string | null;
  message: string;
  created_at: string | null;
}

export interface RecentActivityItem {
  batch_id: string | null;
  tenant_id: number | null;
  tenant_name: string | null;
  stage: string | null;
  status: string | null;
  error_message: string | null;
  timestamp: string | null;
}

export interface TeamHomeResponse {
  assigned_organizations: AssignedOrganization[];
  pipeline_counts: PipelineCounts;
  open_support_messages: OpenSupportMessage[];
  recent_activity: RecentActivityItem[];
}
