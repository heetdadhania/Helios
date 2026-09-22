export interface KPIMetric {
  id: string;
  label: string;
  value: string | number;
  delta: number;
  isPositive: boolean;
  timeframe: string;
  iconName: 'dollar' | 'chart' | 'users' | 'activity' | 'database' | 'shield';
}

export interface ChartDataPoint {
  date: string;
  revenue: number;
  orders: number;
  syncLatency?: number;
}

export interface PendingUpload {
  id: string;
  tenantName: string;
  datasetName: string;
  rowCount: number;
  fileSize: string;
  uploadedAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'processing';
}

export interface PipelineHealth {
  id: string;
  pipelineName: string;
  catalog: string;
  schema: string;
  status: 'healthy' | 'degraded' | 'failed';
  lastSync: string;
  avgDurationSec: number;
  recordsProcessed: number;
}

export interface DataQualityCheck {
  id: string;
  tableName: string;
  tenantSlug: string;
  nullRatePercentage: number;
  duplicateCount: number;
  schemaMatch: boolean;
  score: number;
}

export interface TenantAccount {
  id: string;
  name: string;
  slug: string;
  catalogName: string;
  tier: 'Starter' | 'Growth' | 'Enterprise';
  activePipelines: number;
  status: 'active' | 'suspended';
  createdAt: string;
}
