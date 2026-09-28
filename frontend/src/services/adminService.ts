import api from './api';
import {
  AssignTenantPayload,
  BatchCompleteness,
  ConfirmSchemaPayload,
  ConfirmSchemaResponse,
  CreateTeamMemberPayload,
  CreateTenantPayload,
  DataQualityLogItem,
  PendingUpload,
  SchemaPreview,
  TeamMember,
  Tenant,
} from '@/types/admin';
import { PipelineRun } from '@/types/pipelineHealth';
import { pipelineHealthService } from './pipelineHealthService';

// Default mock pending uploads
const initialPendingUploads: PendingUpload[] = [
  {
    batch_id: 'batch-upl-901',
    tenant_id: '1',
    tenant_name: 'Summit Athletics',
    source_type: 'upload',
    filename: 'q3_sales_transactions.csv',
    file_size_bytes: 4488200,
    row_count: 14200,
    status: 'pending_confirmation',
    created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
  },
  {
    batch_id: 'batch-db-902',
    tenant_id: '2',
    tenant_name: 'Nordic Outfitters',
    source_type: 'db_connection',
    filename: 'orders_export_pg_replica',
    file_size_bytes: 18230000,
    row_count: 58400,
    status: 'pending_confirmation',
    created_at: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
  },
  {
    batch_id: 'batch-api-903',
    tenant_id: '3',
    tenant_name: 'Bluebird Home Decor',
    source_type: 'api_push',
    filename: 'stream_events_channel',
    file_size_bytes: 1200000,
    row_count: 3100,
    status: 'pending_confirmation',
    created_at: new Date(Date.now() - 1000 * 60 * 95).toISOString(),
  },
];

// Default mock schema previews
const mockPreviews: Record<string, SchemaPreview> = {
  'batch-upl-901': {
    batch_id: 'batch-upl-901',
    tenant_id: '1',
    tenant_name: 'Summit Athletics',
    source_type: 'upload',
    inferred_template: 'retail_orders_ecommerce',
    confidence_score: 98.4,
    suggested_silver_table: 'silver.fact_orders',
    column_mappings: [
      { source_column: 'order_id', target_column: 'order_id', inferred_type: 'BIGINT', confidence_score: 1.0, is_nullable: false },
      { source_column: 'customer_id', target_column: 'customer_id', inferred_type: 'BIGINT', confidence_score: 1.0, is_nullable: false },
      { source_column: 'order_date', target_column: 'order_timestamp', inferred_type: 'TIMESTAMP', confidence_score: 0.96, is_nullable: false },
      { source_column: 'product_id', target_column: 'product_id', inferred_type: 'BIGINT', confidence_score: 1.0, is_nullable: false },
      { source_column: 'quantity', target_column: 'units_sold', inferred_type: 'INT', confidence_score: 0.94, is_nullable: false },
      { source_column: 'order_amount', target_column: 'total_revenue', inferred_type: 'DECIMAL(10,2)', confidence_score: 0.98, is_nullable: false },
      { source_column: 'promo_discount', target_column: 'discount_amount', inferred_type: 'DECIMAL(10,2)', confidence_score: 0.92, is_nullable: true },
      { source_column: 'delivery_status', target_column: 'status_code', inferred_type: 'VARCHAR(50)', confidence_score: 0.91, is_nullable: true },
    ],
    sample_rows: [
      { order_id: 1001, customer_id: 840, order_date: '2026-09-01T10:14:00', product_id: 401, quantity: 2, order_amount: 148.50, promo_discount: 10.00, delivery_status: 'Delivered' },
      { order_id: 1002, customer_id: 912, order_date: '2026-09-01T11:22:15', product_id: 402, quantity: 1, order_amount: 89.00, promo_discount: 0.00, delivery_status: 'Shipped' },
      { order_id: 1003, customer_id: 544, order_date: '2026-09-01T12:05:40', product_id: 403, quantity: 4, order_amount: 320.00, promo_discount: 25.00, delivery_status: 'Delivered' },
    ],
    internal_notes: 'Initial automated inference completed with 98.4% confidence score. Validated standard ecommerce orders template.',
  },
};

// Default mock tenants
let mockTenants: Tenant[] = [
  {
    tenant_id: '1',
    name: 'Summit Athletics',
    slug: 'summit_athletics',
    catalog_name: 'helios_catalog',
    schema_name: 'summit_athletics',
    tier: 'Enterprise',
    is_active: true,
    created_at: '2026-08-10T10:00:00Z',
    active_pipelines: 6,
  },
  {
    tenant_id: '2',
    name: 'Nordic Outfitters',
    slug: 'nordic_outfitters',
    catalog_name: 'helios_catalog',
    schema_name: 'nordic_outfitters',
    tier: 'Growth',
    is_active: true,
    created_at: '2026-08-25T14:30:00Z',
    active_pipelines: 4,
  },
  {
    tenant_id: '3',
    name: 'Bluebird Home Decor',
    slug: 'bluebird_home_decor',
    catalog_name: 'helios_catalog',
    schema_name: 'bluebird_home',
    tier: 'Starter',
    is_active: true,
    created_at: '2026-09-02T09:15:00Z',
    active_pipelines: 2,
  },
  {
    tenant_id: '4',
    name: 'Cascade Provisions',
    slug: 'cascade_provisions',
    catalog_name: 'helios_catalog',
    schema_name: 'cascade_provisions',
    tier: 'Starter',
    is_active: false,
    created_at: '2026-07-15T12:00:00Z',
    active_pipelines: 0,
  },
];

// Default mock team members
let mockTeamMembers: TeamMember[] = [
  {
    user_id: 'u-101',
    name: 'Sarah Connor',
    email: 'admin@helios.io',
    role: 'admin',
    is_active: true,
    created_at: '2026-06-01T08:00:00Z',
    assigned_tenants: ['1', '2', '3', '4'],
  },
  {
    user_id: 'u-102',
    name: 'David Miller',
    email: 'team@helios.io',
    role: 'team_member',
    is_active: true,
    created_at: '2026-07-14T11:20:00Z',
    assigned_tenants: ['1', '2'], // Summit & Nordic only
  },
  {
    user_id: 'u-103',
    name: 'Elena Rostova',
    email: 'elena@helios.io',
    role: 'team_member',
    is_active: true,
    created_at: '2026-08-01T09:45:00Z',
    assigned_tenants: ['3'], // Bluebird only
  },
];

// Default mock data quality logs
let mockDataQualityLogs: DataQualityLogItem[] = [
  {
    id: 'dql-501',
    batch_id: 'batch-7f91a2-2026',
    tenant_id: '1',
    tenant_name: 'Summit Athletics',
    table_name: 'silver.fact_orders',
    rejection_reason: 'CurrencyFormatError: Invalid ISO currency symbol "US$" on row 142 in column "order_total"',
    timestamp: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    error_category: 'Type Mismatch',
  },
  {
    id: 'dql-502',
    batch_id: 'batch-e8921f-2026',
    tenant_id: '1',
    tenant_name: 'Summit Athletics',
    table_name: 'bronze.raw_transactions',
    rejection_reason: 'Corrupt header row encountered; file encoding UTF-16LE incompatible with CSV parser.',
    timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    error_category: 'Schema Drift',
  },
  {
    id: 'dql-503',
    batch_id: 'batch-b8104c-2026',
    tenant_id: '2',
    tenant_name: 'Nordic Outfitters',
    table_name: 'silver.dim_customer',
    rejection_reason: 'NullRateThresholdExceeded: Column "customer_email" null rate (14.2%) exceeded strict SLA of 5.0%',
    timestamp: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
    error_category: 'Null Threshold Exceeded',
  },
  {
    id: 'dql-504',
    batch_id: 'batch-d2091a-2026',
    tenant_id: '3',
    tenant_name: 'Bluebird Home Decor',
    table_name: 'silver.fact_shipments',
    rejection_reason: 'DuplicateKeyConstraint: Primary key (tenant_id, shipment_id)=(3, 40182) already committed in Delta transaction 18',
    timestamp: new Date(Date.now() - 1000 * 60 * 420).toISOString(),
    error_category: 'Duplicate Key',
  },
];

export const adminService = {
  /**
   * Module 8: Get list of pending uploads awaiting schema confirmation.
   * Scoped to assigned tenants for Team Members, all tenants for Admins.
   */
  async getPendingUploads(): Promise<PendingUpload[]> {
    try {
      const response = await api.get<PendingUpload[]>('/uploads/pending');
      return response.data;
    } catch {
      return initialPendingUploads;
    }
  },

  /**
   * Module 8: Preview inferred schema and sample rows for a pending batch.
   */
  async getPreview(batchId: string): Promise<SchemaPreview> {
    try {
      const response = await api.get<SchemaPreview>(`/uploads/${batchId}/preview`);
      return response.data;
    } catch {
      if (mockPreviews[batchId]) {
        return mockPreviews[batchId];
      }
      return {
        batch_id: batchId,
        tenant_id: '1',
        tenant_name: 'Summit Athletics',
        source_type: 'upload',
        inferred_template: 'retail_orders_ecommerce',
        confidence_score: 95.0,
        suggested_silver_table: 'silver.fact_orders',
        column_mappings: [
          { source_column: 'order_id', target_column: 'order_id', inferred_type: 'BIGINT', confidence_score: 1.0, is_nullable: false },
          { source_column: 'customer_id', target_column: 'customer_id', inferred_type: 'BIGINT', confidence_score: 1.0, is_nullable: false },
          { source_column: 'order_date', target_column: 'order_timestamp', inferred_type: 'TIMESTAMP', confidence_score: 0.95, is_nullable: false },
          { source_column: 'amount', target_column: 'total_revenue', inferred_type: 'DECIMAL(10,2)', confidence_score: 0.95, is_nullable: false },
        ],
        sample_rows: [
          { order_id: 1, customer_id: 101, order_date: '2026-09-01T12:00:00', amount: 99.99 },
          { order_id: 2, customer_id: 102, order_date: '2026-09-01T12:30:00', amount: 149.50 },
        ],
      };
    }
  },

  /**
   * Module 8: Confirm or override inferred schema mapping and trigger Silver pipeline.
   */
  async confirmUpload(
    batchId: string,
    payload: ConfirmSchemaPayload
  ): Promise<ConfirmSchemaResponse> {
    try {
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
    } catch {
      return {
        batch_id: batchId,
        silver_job_run_id: `run-silver-${Date.now()}`,
        status: 'silver_triggered',
        confirmed_at: new Date().toISOString(),
      };
    }
  },

  /**
   * Module 9: Fetch data completeness indicator for a batch after Silver stage.
   */
  async getCompleteness(batchId: string): Promise<BatchCompleteness> {
    try {
      const response = await api.get<BatchCompleteness>(`/uploads/${batchId}/completeness`);
      return response.data;
    } catch {
      return {
        total_rows: 100,
        accepted_rows: 94,
        rejected_rows: 6,
        completeness_percentage: 94.0,
      };
    }
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
    try {
      const response = await api.get<Tenant[]>('/api/v1/tenants');
      return response.data;
    } catch {
      return [...mockTenants];
    }
  },

  /**
   * Tenants: Create a new tenant. Available to BOTH Team Members and Admins.
   */
  async createTenant(payload: CreateTenantPayload): Promise<Tenant> {
    try {
      const response = await api.post<Tenant>('/api/v1/tenants', payload);
      return response.data;
    } catch {
      const newTenant: Tenant = {
        tenant_id: String(Date.now()),
        name: payload.name,
        slug: payload.slug,
        catalog_name: payload.catalog_name || 'helios_catalog',
        schema_name: payload.schema_name || payload.slug,
        tier: payload.tier || 'Growth',
        is_active: true,
        created_at: new Date().toISOString(),
        active_pipelines: 1,
      };
      mockTenants = [newTenant, ...mockTenants];
      return newTenant;
    }
  },

  /**
   * Tenants: Deactivate a tenant organization. ADMIN ONLY.
   */
  async deactivateTenant(tenantId: string): Promise<{ success: boolean; tenant_id: string; is_active: boolean }> {
    try {
      const response = await api.patch(`/api/v1/tenants/${tenantId}/deactivate`);
      return response.data;
    } catch {
      const tenant = mockTenants.find((t) => String(t.tenant_id) === String(tenantId));
      if (tenant) {
        tenant.is_active = !tenant.is_active;
        return { success: true, tenant_id: tenantId, is_active: tenant.is_active };
      }
      return { success: true, tenant_id: tenantId, is_active: false };
    }
  },

  /**
   * Team Members: List operations team members. ADMIN ONLY.
   */
  async getTeamMembers(): Promise<TeamMember[]> {
    try {
      const response = await api.get<TeamMember[]>('/api/v1/users');
      return response.data;
    } catch {
      return [...mockTeamMembers];
    }
  },

  /**
   * Team Members: Create an operations team member account. ADMIN ONLY.
   */
  async createTeamMember(payload: CreateTeamMemberPayload): Promise<TeamMember> {
    try {
      const response = await api.post<TeamMember>('/api/v1/users', payload);
      return response.data;
    } catch {
      const newMember: TeamMember = {
        user_id: `u-${Date.now()}`,
        name: payload.name,
        email: payload.email,
        role: payload.role,
        is_active: true,
        created_at: new Date().toISOString(),
        assigned_tenants: payload.assigned_tenants || [],
      };
      mockTeamMembers = [newMember, ...mockTeamMembers];
      return newMember;
    }
  },

  /**
   * Team Members: Assign a tenant to a team member. ADMIN ONLY.
   */
  async assignTenant(payload: AssignTenantPayload): Promise<{ success: boolean; user_id: string; tenant_id: string }> {
    try {
      const response = await api.post(`/api/v1/users/${payload.user_id}/assign-tenant`, {
        tenant_id: payload.tenant_id,
      });
      return response.data;
    } catch {
      const member = mockTeamMembers.find((m) => m.user_id === payload.user_id);
      if (member && !member.assigned_tenants.includes(payload.tenant_id)) {
        member.assigned_tenants.push(payload.tenant_id);
      }
      return { success: true, user_id: payload.user_id, tenant_id: payload.tenant_id };
    }
  },

  /**
   * Data Quality: Retrieve rejected rows and schema hygiene audit log items.
   * Filterable by tenant.
   */
  async getDataQualityLogs(tenantFilter?: string): Promise<DataQualityLogItem[]> {
    if (tenantFilter && tenantFilter !== 'all') {
      return mockDataQualityLogs.filter(
        (log) => log.tenant_id === tenantFilter || log.tenant_name.toLowerCase() === tenantFilter.toLowerCase()
      );
    }
    return [...mockDataQualityLogs];
  },
};
