import React, { useMemo } from 'react';
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
import { RevenueTrendResponse, RevenueTrendPoint } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { TrendingUp, Calendar } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface RevenueTrendChartProps {
  data: RevenueTrendResponse | null;
  isLoading?: boolean;
  selectedDays: number;
  onDaysChange: (days: number) => void;
  className?: string;
}

/**
 * Ensures every calendar day in the requested window is present.
 * Days without orders are explicitly assigned 0 revenue and 0 orders.
 */
function fillDailyPoints(
  rawPoints: RevenueTrendPoint[],
  selectedDays: number,
  dataAsOf?: string | null
): RevenueTrendPoint[] {
  if (!rawPoints || rawPoints.length === 0) {
    return [];
  }

  const pointMap = new Map<string, RevenueTrendPoint>();
  for (const pt of rawPoints) {
    if (pt.date) {
      pointMap.set(pt.date, pt);
    }
  }

  // Determine anchor date
  let latestDateStr = dataAsOf;
  if (!latestDateStr) {
    const sorted = [...rawPoints].map((p) => p.date).sort();
    latestDateStr = sorted[sorted.length - 1];
  }

  if (!latestDateStr) {
    return rawPoints;
  }

  const [y, m, d] = latestDateStr.split('-').map(Number);
  const anchorDate = new Date(Date.UTC(y, m - 1, d));

  let startDate: Date;
  if (selectedDays > 0) {
    startDate = new Date(anchorDate);
    startDate.setUTCDate(anchorDate.getUTCDate() - (selectedDays - 1));
  } else {
    const sorted = [...rawPoints].map((p) => p.date).sort();
    const [sy, sm, sd] = sorted[0].split('-').map(Number);
    startDate = new Date(Date.UTC(sy, sm - 1, sd));
  }

  const result: RevenueTrendPoint[] = [];
  const curr = new Date(startDate);
  while (curr <= anchorDate) {
    const dateStr = curr.toISOString().slice(0, 10);
    const existing = pointMap.get(dateStr);
    if (existing) {
      result.push(existing);
    } else {
      result.push({
        date: dateStr,
        total_revenue: 0,
        total_orders: 0,
        avg_order_value: 0,
        total_quantity: 0,
      });
    }
    curr.setUTCDate(curr.getUTCDate() + 1);
  }

  return result;
}

export const RevenueTrendChart: React.FC<RevenueTrendChartProps> = React.memo(({
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

  const { chartPoints, revenueTicks, maxRevenueTick, orderTicks, maxOrderTick } = useMemo(() => {
    const points = fillDailyPoints(data?.points || [], selectedDays, data?.data_as_of);

    if (points.length === 0) {
      return {
        chartPoints: [],
        revenueTicks: [0, 5000, 10000, 15000, 20000],
        maxRevenueTick: 20000,
        orderTicks: [0, 1, 2, 3, 4],
        maxOrderTick: 4,
      };
    }

    const maxRev = Math.max(...points.map((p) => p.total_revenue), 0);
    const maxOrd = Math.max(...points.map((p) => p.total_orders), 0);

    // Compute nice, evenly spaced ticks for revenue (Left Axis)
    let revStep = 5000;
    let revMax = 20000;

    if (maxRev <= 0) {
      revStep = 5000;
      revMax = 20000;
    } else {
      const targetSteps = 4;
      const rawStep = maxRev / targetSteps;
      const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
      const residual = rawStep / magnitude;
      let stepMultiplier = 1;
      if (residual <= 1) stepMultiplier = 1;
      else if (residual <= 2) stepMultiplier = 2;
      else if (residual <= 2.5) stepMultiplier = 2.5;
      else if (residual <= 5) stepMultiplier = 5;
      else stepMultiplier = 10;

      revStep = stepMultiplier * magnitude;
      revMax = Math.ceil(maxRev / revStep) * revStep;
      if (revMax === 0) revMax = revStep * targetSteps;
    }

    const revTicks: number[] = [];
    for (let t = 0; t <= revMax; t += revStep) {
      revTicks.push(t);
    }

    // Compute nice whole-number ticks for orders (Right Axis)
    let ordStep = 1;
    let ordMax = 4;

    if (maxOrd <= 4) {
      ordStep = 1;
      ordMax = Math.max(2, maxOrd);
    } else {
      const rawOrdStep = maxOrd / 4;
      ordStep = Math.max(1, Math.ceil(rawOrdStep));
      ordMax = ordStep * 4;
      while (ordMax < maxOrd) {
        ordMax += ordStep;
      }
    }

    const ordTicks: number[] = [];
    for (let o = 0; o <= ordMax; o += ordStep) {
      ordTicks.push(o);
    }

    return {
      chartPoints: points,
      revenueTicks: revTicks,
      maxRevenueTick: revMax,
      orderTicks: ordTicks,
      maxOrderTick: ordMax,
    };
  }, [data, selectedDays]);

  if (isLoading) {
    return (
      <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark animate-pulse ${className}`}>
        <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-4 w-72 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const hasData = chartPoints.length > 0;
  const avgDailyRevenue = chartPoints.length > 0 ? (data?.total_revenue || 0) / chartPoints.length : 0;

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
            { days: 0, label: 'All' },
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
              {formatINR(data?.total_revenue || 0)}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Total Orders</span>
            <div className="text-base font-bold text-helios-accent-blue mt-0.5">
              {formatCountIN(data?.total_orders || 0)}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Average Daily Revenue</span>
            <div className="text-base font-bold text-helios-accent-teal mt-0.5">
              {formatINR(avgDailyRevenue)}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-400">Window Scope</span>
            <div className="text-base font-bold text-slate-400 mt-0.5">
              {selectedDays ? `Last ${selectedDays} Days` : 'All Time'}
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
            Adjust the lookback window or contact your operations team to view historical store performance.
          </p>
        </div>
      ) : (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartPoints} margin={{ top: 10, right: 25, left: 15, bottom: 0 }}>
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
                width={75}
                ticks={revenueTicks}
                domain={[0, maxRevenueTick]}
                tickFormatter={(v) => formatINRCompact(v)}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke={textColor}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                width={40}
                allowDecimals={false}
                ticks={orderTicks}
                domain={[0, maxOrderTick]}
                tickFormatter={(v) => formatCountIN(v)}
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
                  name === 'Revenue (₹)' ? formatINR(Number(value)) : formatCountIN(Number(value)),
                  name,
                ]}
                labelFormatter={(label: any) => {
                  try {
                    const d = new Date(label);
                    return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
                  } catch {
                    return label;
                  }
                }}
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
                type="linear"
                dataKey="total_revenue"
                name="Revenue (₹)"
                stroke="#3B82F6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#revenueGradient)"
                dot={{ r: 3, fill: '#3B82F6', strokeWidth: 1.5, stroke: isDark ? '#161616' : '#FFFFFF' }}
                activeDot={{ r: 5, fill: '#3B82F6', strokeWidth: 2, stroke: isDark ? '#161616' : '#FFFFFF' }}
              />
              <Area
                yAxisId="right"
                type="linear"
                dataKey="total_orders"
                name="Order Volume"
                stroke="#10B981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#ordersGradient)"
                dot={{ r: 3, fill: '#10B981', strokeWidth: 1.5, stroke: isDark ? '#161616' : '#FFFFFF' }}
                activeDot={{ r: 5, fill: '#10B981', strokeWidth: 2, stroke: isDark ? '#161616' : '#FFFFFF' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
});

RevenueTrendChart.displayName = 'RevenueTrendChart';

export default RevenueTrendChart;
