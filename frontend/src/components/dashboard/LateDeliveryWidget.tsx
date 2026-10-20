import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { LateDeliveryRiskResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Truck, AlertTriangle, Clock } from 'lucide-react';
import { formatCountIN } from '@/utils/currency';

interface LateDeliveryWidgetProps {
  data: LateDeliveryRiskResponse | null;
  isLoading?: boolean;
  className?: string;
}

export const LateDeliveryWidget: React.FC<LateDeliveryWidgetProps> = React.memo(({
  data,
  isLoading = false,
  className = '',
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const tooltipBg = isDark ? '#161616' : '#FFFFFF';
  const tooltipBorder = isDark ? '#262626' : '#E5E7EB';

  if (isLoading) {
    return (
      <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark animate-pulse ${className}`}>
        <div className="h-5 w-44 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-3 w-64 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const hasData = (data?.total_shipments || 0) > 0;

  const chartData = useMemo(
    () =>
      [
        { name: 'On-Time', value: data?.on_time_shipments || 0, color: '#10B981' },
        { name: 'Late Shipments', value: data?.late_shipments || 0, color: '#EF4444' },
      ].filter((d) => d.value > 0),
    [data?.on_time_shipments, data?.late_shipments]
  );

  const lateRate = data?.late_rate_pct || 0;
  const isHealthy = lateRate <= 5.0;

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Truck className="w-5 h-5 text-helios-accent-teal" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Fulfillment SLA & Delivery Risk
            </h3>
          </div>
          <span
            className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
              isHealthy
                ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-600 border-rose-500/20'
            }`}
          >
            {isHealthy ? 'SLA Compliant' : 'Risk Elevated'}
          </span>
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Carrier transit velocity and punctuality joined across <code className="font-mono text-helios-accent-blue">gold.fact_shipments</code> and <code className="font-mono text-helios-accent-blue">dim_delivery_status</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Truck className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No fulfillment records available
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Connect a shipping carrier or upload fulfillment datasets to analyze delivery risk.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
            {/* Donut Chart */}
            <div className="w-full h-48 relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      borderColor: tooltipBorder,
                      borderRadius: '10px',
                      color: isDark ? '#F5F5F5' : '#111827',
                      fontSize: '12px',
                    }}
                    formatter={(val: any, name: string) => [`${formatCountIN(val)} shipments`, name]}
                  />
                  <Pie
                    data={chartData}
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Inner Center Metric */}
              <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none">
                <span className="text-xl font-bold font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {(100 - lateRate).toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                  On-Time
                </span>
              </div>
            </div>

            {/* Quick Metrics Column */}
            <div className="space-y-2.5 text-xs">
              <div className="p-2.5 rounded-lg bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
                <span className="text-slate-400">Total Shipments</span>
                <span className="font-mono font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.total_shipments || 0)}
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-rose-500/[0.04] border border-rose-500/20 flex items-center justify-between">
                <span className="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                  Late Deliveries
                </span>
                <span className="font-mono font-bold text-rose-600 dark:text-rose-400">
                  {formatCountIN(data?.late_shipments || 0)} ({lateRate}%)
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  Avg Shipping Transit
                </span>
                <span className="font-mono font-bold text-helios-accent-teal">
                  {data?.avg_shipping_days || 0} days
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Breakdown footer */}
      {hasData && data?.status_breakdown && data.status_breakdown.length > 0 && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark flex items-center justify-between text-[11px] text-slate-400">
          <span>SLA Punctuality Target: &gt; 95%</span>
          <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
            {data.on_time_shipments} On-Time Fulfilled
          </span>
        </div>
      )}
    </div>
  );
});

LateDeliveryWidget.displayName = 'LateDeliveryWidget';

export default LateDeliveryWidget;
