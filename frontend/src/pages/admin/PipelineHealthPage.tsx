import React from 'react';
import { KPICard } from '@/components/KPICard';
import { LineChartCard } from '@/components/LineChartCard';
import { KPIMetric, ChartDataPoint, PipelineHealth } from '@/types/data';

const adminMetrics: KPIMetric[] = [
  {
    id: 'kpi_healthy_pipes',
    label: 'Healthy Pipelines',
    value: '24 / 24',
    delta: 100,
    isPositive: true,
    timeframe: 'SLA target',
    iconName: 'activity',
  },
  {
    id: 'kpi_sync_throughput',
    label: 'Daily Ingestion Rate',
    value: '42.8M rows',
    delta: 12.4,
    isPositive: true,
    timeframe: 'vs last week',
    iconName: 'database',
  },
  {
    id: 'kpi_median_latency',
    label: 'Median Sync Latency',
    value: '138 ms',
    delta: 8.5,
    isPositive: true,
    timeframe: 'vs last week',
    iconName: 'chart',
  },
  {
    id: 'kpi_active_tenants',
    label: 'Active Tenants',
    value: '18',
    delta: 5.5,
    isPositive: true,
    timeframe: 'this month',
    iconName: 'users',
  },
];

const latencyTrends: ChartDataPoint[] = [
  { date: '00:00', revenue: 140, orders: 12 },
  { date: '04:00', revenue: 132, orders: 8 },
  { date: '08:00', revenue: 185, orders: 25 },
  { date: '12:00', revenue: 210, orders: 40 },
  { date: '16:00', revenue: 165, orders: 32 },
  { date: '20:00', revenue: 142, orders: 18 },
];

const pipelineStatuses: PipelineHealth[] = [
  {
    id: 'pipe_1',
    pipelineName: 'Shopify Delta Realtime Sync',
    catalog: 'helios_catalog',
    schema: 'acme_retail',
    status: 'healthy',
    lastSync: '45 seconds ago',
    avgDurationSec: 1.2,
    recordsProcessed: 1420500,
  },
  {
    id: 'pipe_2',
    pipelineName: 'Stripe Webhook Streaming Ingestion',
    catalog: 'helios_catalog',
    schema: 'nordic_outfitters',
    status: 'healthy',
    lastSync: '2 minutes ago',
    avgDurationSec: 0.8,
    recordsProcessed: 320900,
  },
  {
    id: 'pipe_3',
    pipelineName: 'Nightly Parquet Reconciliation',
    catalog: 'helios_catalog',
    schema: 'system_recon',
    status: 'healthy',
    lastSync: '4 hours ago',
    avgDurationSec: 42.5,
    recordsProcessed: 8900140,
  },
];

export const PipelineHealthPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Databricks Unity Catalog & Delta Telemetry
        </h2>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
          Real-time health monitoring of multi-tenant streaming pipelines and query latency.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {adminMetrics.map((metric) => (
          <KPICard key={metric.id} metric={metric} />
        ))}
      </div>

      {/* Latency Chart */}
      <LineChartCard
        title="Ingestion Latency & Throughput Pulse"
        subtitle="End-to-end commit latency into Unity Catalog Delta Lake"
        data={latencyTrends}
      />

      {/* Active Pipelines Table */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
        <h3 className="text-base font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-4">
          Production Pipeline Status
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">Pipeline</th>
                <th className="pb-3 font-semibold">Catalog / Schema</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold">Processed Records</th>
                <th className="pb-3 font-semibold">Avg Duration</th>
                <th className="pb-3 font-semibold">Last Sync</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
              {pipelineStatuses.map((pipe) => (
                <tr key={pipe.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {pipe.pipelineName}
                  </td>
                  <td className="py-3 font-mono text-helios-accent-blue">
                    {pipe.catalog}.{pipe.schema}
                  </td>
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-helios-accent-teal">
                      Healthy
                    </span>
                  </td>
                  <td className="py-3">{pipe.recordsProcessed.toLocaleString()}</td>
                  <td className="py-3 font-mono">{pipe.avgDurationSec}s</td>
                  <td className="py-3 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    {pipe.lastSync}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
