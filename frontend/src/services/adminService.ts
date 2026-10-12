import api from './api';
import {
  AssignTenantPayload,
  BatchCompleteness,
  ColumnMapping,
  ConfirmSchemaPayload,
  ConfirmSchemaResponse,
  CreateTeamMemberPayload,
  CreateTeamMemberResponse,
  CreateTenantPayload,
  DataQualityLogItem,
  PendingUpload,
  SchemaPreview,
  TeamMember,
  Tenant,
} from '@/types/admin';
import { PipelineRun } from '@/types/pipelineHealth';
import { pipelineHealthService } from './pipelineHealthService';

export const adminService = {
  /**
   * Module 8: Get list of pending uploads awaiting schema confirmation.
   * Scoped to assigned tenants for Team Members, all tenants for Admins.
   */
  async getPendingUploads(): Promise<PendingUpload[]> {
    const response = await api.get<PendingUpload[]>('/uploads/pending');
    return response.data;
  },

  /**
   * Module 8: Preview inferred schema and sample rows for a pending batch.
   */
  async getPreview(batchId: string): Promise<SchemaPreview> {
    const response = await api.get<any>(`/uploads/${batchId}/preview`);
    const data = response.data || {};

    const rawMapping = data.column_mapping || data.column_mappings || {};
    let mappingsArray: ColumnMapping[] = [];

    if (Array.isArray(rawMapping)) {
      mappingsArray = rawMapping.map((item: any) => ({
        source_column: item.source_column || item.incoming_column || '',
        target_field: item.target_field ?? item.target_column ?? null,
        target_column: item.target_field ?? item.target_column ?? '',
        inferred_type: item.inferred_type || 'string',
        similarity_score: item.similarity_score ?? item.confidence_score ?? (item.score ? item.score / 100 : 0),
        confidence_score: item.similarity_score ?? item.confidence_score ?? 0,
        is_exact: Boolean(item.is_exact),
        is_nullable: item.is_nullable ?? true,
      }));
    } else if (rawMapping && typeof rawMapping === 'object') {
      mappingsArray = Object.entries(rawMapping).map(([key, val]: [string, any]) => {
        const isObj = val && typeof val === 'object';
        const sourceCol = isObj ? (val.incoming_column || key) : key;
        const targetField = isObj ? (val.target_field ?? null) : (val ?? null);
        const inferredType = isObj ? (val.inferred_type || 'string') : 'string';
        const simScore = isObj ? (val.similarity_score ?? 0) : 1.0;
        const isExact = isObj ? Boolean(val.is_exact) : false;

        return {
          source_column: sourceCol,
          target_field: targetField,
          target_column: targetField || '',
          inferred_type: inferredType,
          similarity_score: typeof simScore === 'number' && simScore > 1 ? simScore / 100 : Number(simScore || 0),
          confidence_score: typeof simScore === 'number' && simScore > 1 ? simScore / 100 : Number(simScore || 0),
          is_exact: isExact,
          is_nullable: true,
        };
      });
    }

    return {
      batch_id: data.batch_id || batchId,
      tenant_id: String(data.tenant_id || ''),
      tenant_name: data.tenant_name,
      source_type: data.source_type || 'upload',
      inferred_template: data.detected_template || data.inferred_template || 'template_orders',
      detected_template: data.detected_template || data.inferred_template || 'template_orders',
      confidence_score: typeof data.confidence_score === 'number' ? data.confidence_score : 0,
      suggested_silver_table: data.suggested_silver_table || (data.detected_template === 'template_shipping' ? 'silver.shipping_clean' : 'silver.orders_clean'),
      column_mappings: mappingsArray,
      sample_rows: Array.isArray(data.sample_rows) ? data.sample_rows : [],
      internal_notes: data.internal_notes || null,
      unmapped_required_fields: Array.isArray(data.unmapped_required_fields) ? data.unmapped_required_fields : [],
    };
  },

  /**
   * Module 8: Confirm or override inferred schema mapping and trigger Silver pipeline.
   */
  async confirmUpload(
    batchId: string,
    payload: ConfirmSchemaPayload
  ): Promise<ConfirmSchemaResponse> {
    const response = await api.post<ConfirmSchemaResponse>(
      `/uploads/${batchId}/confirm`,
      {
        confirmed_template: payload.confirmed_template || 'template_orders',
        corrected_mapping: payload.column_mappings,
        internal_notes: payload.internal_notes || payload.notes,
        ...payload,
      }
    );
    return response.data;
  },

  /**
   * Reject a pending upload with a mandatory reason.
   */
  async rejectUpload(batchId: string, reason: string): Promise<any> {
    const response = await api.post(`/uploads/${batchId}/reject`, { reason });
    return response.data;
  },


  /**
   * Module 9: Fetch data completeness indicator for a batch after Silver stage.
   */
  async getCompleteness(batchId: string): Promise<BatchCompleteness> {
    const response = await api.get<BatchCompleteness>(`/uploads/${batchId}/completeness`);
    return response.data;
  },

  /**
   * Module 12: Get pipeline execution runs.
   */
  async getPipelineRuns(status?: string): Promise<PipelineRun[]> {
    return pipelineHealthService.listRuns(status);
  },

  /**
   * Tenants: List tenants.
   */
  async getTenants(): Promise<Tenant[]> {
    const response = await api.get<Tenant[]>('/tenants');
    return response.data;
  },

  /**
   * Tenants: Create a new tenant. Available to BOTH Team Members and Admins.
   */
  async createTenant(payload: CreateTenantPayload): Promise<Tenant> {
    const response = await api.post<Tenant>('/tenants', payload);
    return response.data;
  },

  /**
   * Tenants: Deactivate a tenant organization. ADMIN ONLY.
   */
  async deactivateTenant(tenantId: string): Promise<{ success: boolean; tenant_id: string; is_active: boolean }> {
    const response = await api.patch<{ success: boolean; tenant_id: string; is_active: boolean }>(`/tenants/${tenantId}/deactivate`);
    return response.data;
  },

  /**
   * Team Members: List operations team members. ADMIN ONLY.
   */
  async getTeamMembers(): Promise<TeamMember[]> {
    const response = await api.get<TeamMember[]>('/team-members');
    return response.data;
  },

  /**
   * Team Members: Create an operations team member account. ADMIN ONLY.
   * Returns created member with generated temporary password.
   */
  async createTeamMember(payload: CreateTeamMemberPayload): Promise<CreateTeamMemberResponse> {
    const formattedPayload = {
      name: payload.name,
      email: payload.email,
      phone_number: payload.phone_number,
      role: payload.role,
      staff_id: payload.staff_id || null,
      designation: payload.designation || null,
      tenant_ids: payload.tenant_ids || (payload.assigned_tenants ? payload.assigned_tenants.map(Number).filter((n) => !isNaN(n)) : []),
    };
    const response = await api.post<CreateTeamMemberResponse>('/team-members', formattedPayload);
    return response.data;
  },

  /**
   * Team Members: Replace tenant assignments for a team member. ADMIN ONLY.
   */
  async replaceAssignments(userId: string | number, tenantIds: number[]): Promise<TeamMember> {
    const response = await api.put<TeamMember>(`/team-members/${userId}/assignments`, {
      tenant_ids: tenantIds,
    });
    return response.data;
  },

  /**
   * Team Members: Activate or deactivate a team member account. ADMIN ONLY.
   */
  async toggleTeamMemberActive(userId: string | number, isActive: boolean): Promise<TeamMember> {
    const response = await api.patch<TeamMember>(`/team-members/${userId}/active`, {
      is_active: isActive,
    });
    return response.data;
  },

  /**
   * Team Members: Legacy assign single tenant (for compatibility).
   */
  async assignTenant(payload: AssignTenantPayload): Promise<{ success: boolean; user_id: string; tenant_id: string }> {
    const response = await api.post<{ success: boolean; user_id: string; tenant_id: string }>(`/team-members/${payload.user_id}/assign-tenant`, {
      tenant_id: payload.tenant_id,
    });
    return response.data;
  },

  /**
   * Data Quality: Retrieve rejected rows and schema hygiene audit log items.
   * Filterable by tenant and batch. Connected to real GET /api/data-quality/logs.
   */
  async getDataQualityLogs(tenantFilter?: string, batchId?: string): Promise<DataQualityLogItem[]> {
    const params: Record<string, any> = {};
    if (tenantFilter && tenantFilter !== 'all') {
      const num = Number(tenantFilter);
      if (!isNaN(num)) {
        params.tenant_id = num;
      }
    }
    if (batchId) {
      params.batch_id = batchId;
    }
    const response = await api.get<DataQualityLogItem[]>('/data-quality/logs', { params });
    return response.data;
  },
};
