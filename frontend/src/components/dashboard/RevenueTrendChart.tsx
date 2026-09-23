import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { RevenueTrendResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { TrendingUp, Calendar } from 'lucide-react';

interface RevenueTrendChartProps {
  data: RevenueTrendResponse | null;
  isLoading?: boolean;
  selectedDays: number;
  onDaysChange: (days: number) => void;
  className?: string;
}

export const RevenueTrendChart: React.FC<RevenueTrendChartProps> = ({
  data,
  isLoading = false,
  selectedDays,
  onDaysChange,
  className = '',
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const gridColor = isDark ? '#262626' : '#E5E7EB';
  const textColor = isDark ? '#A3A3A3' : '#6B7280';
  const tooltipBg = isDark ? '#161616' : '#FFFFFF';
  const tooltipBorder = isDark ? '#262626' : '#E5E7EB';

  if (isLoading) {
    return (
      <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark animate-pulse ${className}`}>
        <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-4 w-72 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const points = data?.points || [];
  const hasData = points.length > 0;

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm ${className}`}>
      {/* Widget Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-helios-accent-blue" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Daily Revenue & Order Velocity
            </h3>
          </div>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Aggregated Gold-layer transaction volume and store receipts from <code className="font-mono text-helios-accent-blue">gold.fact_orders_daily_summary</code>
          </p>
        </div>

        {/* Lookback Filter Tabs */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto bg-black/5 dark:bg-white/5 p-1 rounded-lg border border-helios-border-light dark:border-helios-border-dark">
          {[
            { days: 7, label: '7D' },
            { days: 30, label: '30D' },
            { days: 90, label: '90D' },
          ].map((tab) => (
            <button
              key={tab.days}
              type="button"
              onClick={() => onDaysChange(tab.days)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                selectedDays === tab.days
                  ? 'bg-helios-accent-blue text-white shadow-sm'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Highlights Bar */}
      {hasData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 p-3 rounded-lg bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-xs">
          <div>
            <span className="text-[11px] text-slate-400">Total Period Revenue</span>
            <div className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-0.5">
              ${(data?.total_revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Total Orders</span>
            <div className="text-base font-bold text-helios-accent-blue mt-0.5">
              {(data?.total_orders || 0).toLocaleString()}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Average Daily Revenue</span>
            <div className="text-base font-bold text-helios-accent-teal mt-0.5">
              ${(points.length > 0 ? (data?.total_revenue || 0) / points.length : 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Window Scope</span>
            <div className="text-base font-bold text-slate-400 mt-0.5">
              Last {selectedDays} Days
            </div>
          </div>
        </div>
      )}

      {/* Chart Canvas or Empty State */}
      {!hasData ? (
        <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
          <Calendar className="w-8 h-8 text-slate-400 mb-2" />
          <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            No revenue records found for this period
          </h4>
          <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 max-w-sm">
            Connect a data source or adjust the lookback window to view historical store performance.
          </p>
        </div>
      ) : (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
              <XAxis
                dataKey="date"
                stroke={textColor}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => {
                  try {
                    const d = new Date(v);
                    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
                  } catch {
                    return v;
                  }
                }}
              />
              <YAxis
                yAxisId="left"
                stroke={textColor}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke={textColor}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: tooltipBg,
                  borderColor: tooltipBorder,
                  borderRadius: '10px',
                  color: isDark ? '#F5F5F5' : '#111827',
                  fontSize: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                }}
                formatter={(value: any, name: string) => [
                  name === 'Revenue ($)' ? `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : value,
                  name,
                ]}
              />
              <Legend
                wrapperStyle={{
                  fontSize: '12px',
                  paddingTop: '12px',
                  color: textColor,
                }}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="total_revenue"
                name="Revenue ($)"
                stroke="#3B82F6"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#revenueGradient)"
              />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="total_orders"
                name="Order Volume"
                stroke="#10B981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#ordersGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default RevenueTrendChart;
