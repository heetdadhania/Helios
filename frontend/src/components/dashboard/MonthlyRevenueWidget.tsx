import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { MonthlyRevenueResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { CalendarDays, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface MonthlyRevenueWidgetProps {
  data: MonthlyRevenueResponse | null;
  isLoading?: boolean;
  className?: string;
}

export const MonthlyRevenueWidget: React.FC<MonthlyRevenueWidgetProps> = React.memo(({
  data,
  isLoading = false,
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
        <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-3 w-64 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const months = data?.months || [];
  const hasData = months.length > 0;

  const chartData = useMemo(
    () =>
      months.map((m) => ({
        month_name: m.month_name,
        month_key: m.month_key,
        revenue: typeof m.revenue === 'string' ? parseFloat(m.revenue) : m.revenue,
        previous_revenue:
          m.previous_month_revenue !== null
            ? typeof m.previous_month_revenue === 'string'
              ? parseFloat(m.previous_month_revenue)
              : m.previous_month_revenue
            : null,
        mom_growth_pct: m.mom_growth_pct,
        order_count: m.order_count,
      })),
    [months]
  );

  // Latest month MoM stat
  const latestMonth = months.length > 0 ? months[months.length - 1] : null;

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <CalendarDays className="w-5 h-5 text-emerald-500" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Month-over-Month Revenue
            </h3>
          </div>
          {latestMonth?.mom_growth_pct !== null && latestMonth?.mom_growth_pct !== undefined && (
            <div className="flex items-center gap-1.5">
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  latestMonth.mom_growth_pct > 0
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                    : latestMonth.mom_growth_pct < 0
                    ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
                    : 'bg-slate-500/10 text-slate-500 border-slate-500/20'
                }`}
              >
                {latestMonth.mom_growth_pct > 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : latestMonth.mom_growth_pct < 0 ? (
                  <TrendingDown className="w-3 h-3" />
                ) : (
                  <Minus className="w-3 h-3" />
                )}
                <span>
                  Latest MoM: {latestMonth.mom_growth_pct > 0 ? '+' : ''}
                  {latestMonth.mom_growth_pct.toFixed(2)}%
                </span>
              </span>
            </div>
          )}
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Chronological monthly performance aggregated across <code className="font-mono text-helios-accent-blue">gold.fact_orders</code> and <code className="font-mono text-helios-accent-blue">dim_date</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <CalendarDays className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No monthly sales recorded
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Monthly revenue and growth progression will appear as orders span calendar periods.
            </p>
          </div>
        ) : (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis
                  dataKey="month_name"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => formatINRCompact(v)}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      const mom = d.mom_growth_pct;
                      return (
                        <div
                          style={{
                            backgroundColor: tooltipBg,
                            borderColor: tooltipBorder,
                            borderRadius: '10px',
                            borderWidth: '1px',
                            padding: '10px 14px',
                            color: isDark ? '#F5F5F5' : '#111827',
                            fontSize: '12px',
                            boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                          }}
                        >
                          <div className="font-bold text-sm mb-1">{d.month_name}</div>
                          <div className="text-xs text-helios-accent-blue font-semibold mb-1">
                            Revenue: {formatINR(d.revenue)}
                          </div>
                          <div className="text-[11px] text-slate-400 mb-1.5">
                            Orders: {formatCountIN(d.order_count)}
                          </div>
                          <div className="pt-1 border-t border-slate-200 dark:border-slate-800 flex items-center gap-1.5 text-xs">
                            <span className="text-slate-400">MoM Change:</span>
                            {mom !== null && mom !== undefined ? (
                              <span
                                className={`font-semibold ${
                                  mom > 0
                                    ? 'text-emerald-500'
                                    : mom < 0
                                    ? 'text-rose-500'
                                    : 'text-slate-400'
                                }`}
                              >
                                {mom > 0 ? '+' : ''}
                                {mom.toFixed(2)}%
                              </span>
                            ) : (
                              <span className="text-slate-400 italic">
                                Baseline (First month)
                              </span>
                            )}
                          </div>
                          {d.previous_revenue !== null && d.previous_revenue !== undefined && (
                            <div className="text-[10px] text-slate-400 mt-0.5">
                              Prev Month: {formatINR(d.previous_revenue)}
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="revenue" fill="#10B981" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => {
                    const mom = entry.mom_growth_pct;
                    let barColor = '#10B981'; // Default emerald
                    if (mom !== null && mom < 0) {
                      barColor = '#F43F5E'; // Rose if negative growth
                    } else if (mom !== null && mom > 0) {
                      barColor = '#10B981'; // Emerald if positive growth
                    }
                    return <Cell key={`month-bar-${index}`} fill={barColor} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Monthly Timeline Breakdown */}
      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            {months.map((m) => (
              <div
                key={m.month_key}
                className="p-2 rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark flex flex-col justify-between"
              >
                <div className="flex items-center justify-between text-slate-400 text-[10px]">
                  <span>{m.month_name}</span>
                  {m.mom_growth_pct !== null ? (
                    <span
                      className={`font-semibold ${
                        m.mom_growth_pct > 0
                          ? 'text-emerald-500'
                          : m.mom_growth_pct < 0
                          ? 'text-rose-500'
                          : 'text-slate-400'
                      }`}
                    >
                      {m.mom_growth_pct > 0 ? '+' : ''}
                      {m.mom_growth_pct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </div>
                <div className="font-mono font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-1">
                  {formatINR(m.revenue)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

MonthlyRevenueWidget.displayName = 'MonthlyRevenueWidget';

export default MonthlyRevenueWidget;

