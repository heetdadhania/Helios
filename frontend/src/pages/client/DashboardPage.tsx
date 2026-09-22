import React from 'react';
import { KPICard } from '@/components/KPICard';
import { LineChartCard } from '@/components/LineChartCard';
import { KPIMetric, ChartDataPoint } from '@/types/data';

const clientMetrics: KPIMetric[] = [
  {
    id: 'kpi_revenue',
    label: 'Total Revenue',
    value: '$148,290',
    delta: 14.8,
    isPositive: true,
    timeframe: 'last month',
    iconName: 'dollar',
  },
  {
    id: 'kpi_orders',
    label: 'Processed Orders',
    value: '4,812',
    delta: 8.2,
    isPositive: true,
    timeframe: 'last month',
    iconName: 'chart',
  },
  {
    id: 'kpi_aov',
    label: 'Average Order Value',
    value: '$30.82',
    delta: 2.1,
    isPositive: false,
    timeframe: 'last month',
    iconName: 'activity',
  },
  {
    id: 'kpi_sync',
    label: 'Delta Lake Latency',
    value: '184 ms',
    delta: 18.5,
    isPositive: true,
    timeframe: 'yesterday',
    iconName: 'database',
  },
];

const trendData: ChartDataPoint[] = [
  { date: 'Sep 1', revenue: 12000, orders: 380 },
  { date: 'Sep 5', revenue: 15400, orders: 490 },
  { date: 'Sep 9', revenue: 14200, orders: 440 },
  { date: 'Sep 13', revenue: 19800, orders: 610 },
  { date: 'Sep 17', revenue: 23100, orders: 740 },
  { date: 'Sep 21', revenue: 21500, orders: 690 },
];

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Top Welcome / Tenant Subheader */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Store Performance & Telemetry
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            Synchronized directly with Databricks Unity Catalog (<code className="font-mono text-helios-accent-blue">helios_catalog.ecommerce</code>)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-helios-accent-teal/10 text-helios-accent-teal border border-helios-accent-teal/20">
            <span className="w-1.5 h-1.5 rounded-full bg-helios-accent-teal animate-ping" />
            Live Sync Active
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {clientMetrics.map((metric) => (
          <KPICard key={metric.id} metric={metric} />
        ))}
      </div>

      {/* Main Chart Section */}
      <LineChartCard
        title="Revenue & Order Velocity"
        subtitle="Daily aggregate orders ingested through Delta Lake streaming connector"
        data={trendData}
      />

      {/* Recent Transactions / Synced Datasets Table */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
        <h3 className="text-base font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-4">
          Recent Synced Ingestion Batches
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">Table / Source</th>
                <th className="pb-3 font-semibold">Ingested Rows</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold">Latency</th>
                <th className="pb-3 font-semibold">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              <tr>
                <td className="py-3 font-mono text-helios-accent-blue font-medium">orders_stream_v2</td>
                <td className="py-3">1,482 records</td>
                <td className="py-3">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-helios-accent-teal text-[11px] font-semibold">
                    Committed
                  </span>
                </td>
                <td className="py-3 font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">128ms</td>
                <td className="py-3 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">2 mins ago</td>
              </tr>
              <tr>
                <td className="py-3 font-mono text-helios-accent-blue font-medium">customer_events_raw</td>
                <td className="py-3">9,840 records</td>
                <td className="py-3">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-helios-accent-teal text-[11px] font-semibold">
                    Committed
                  </span>
                </td>
                <td className="py-3 font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">195ms</td>
                <td className="py-3 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">14 mins ago</td>
              </tr>
              <tr>
                <td className="py-3 font-mono text-helios-accent-blue font-medium">inventory_snapshots</td>
                <td className="py-3">420 records</td>
                <td className="py-3">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-helios-accent-teal text-[11px] font-semibold">
                    Committed
                  </span>
                </td>
                <td className="py-3 font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">140ms</td>
                <td className="py-3 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">1 hour ago</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
