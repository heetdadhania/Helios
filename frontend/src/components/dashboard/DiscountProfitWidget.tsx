import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { DiscountVsProfitResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Percent } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface DiscountProfitWidgetProps {
  data: DiscountVsProfitResponse | null;
  isLoading?: boolean;
  className?: string;
}

export const DiscountProfitWidget: React.FC<DiscountProfitWidgetProps> = React.memo(({
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
        <div className="h-5 w-44 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-3 w-64 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const bands = data?.bands || [];
  const hasData = bands.length > 0;

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Percent className="w-5 h-5 text-indigo-500" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Discount vs Profit Elasticity
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
              Avg Margin: {data?.overall_profit_margin_pct || 0}%
            </span>
          </div>
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Gross margin sensitivity across promotional discount tiers calculated in <code className="font-mono text-helios-accent-blue">gold.fact_orders</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Percent className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No discount tiers detected
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Add discount promotions or transaction records to evaluate pricing sensitivity.
            </p>
          </div>
        ) : (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bands} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis dataKey="band" stroke={textColor} fontSize={11} tickLine={false} axisLine={false} />
                <YAxis
                  yAxisId="left"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => formatINRCompact(v)}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}%`}
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
                  formatter={(val: any, name: string) => [
                    name.includes('Margin')
                      ? `${Number(val).toFixed(1)}%`
                      : formatINR(Number(val)),
                    name,
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar yAxisId="left" dataKey="total_revenue" name="Revenue (₹)" fill="#6366F1" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="left" dataKey="total_profit" name="Net Profit (₹)" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark flex items-center justify-between text-[11px] text-slate-400">
          <span>Overall Discount Rate: <strong className="font-mono text-helios-accent-blue">{data?.overall_discount_rate_pct}%</strong></span>
          <span>Orders Tracked: <strong className="font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">{formatCountIN(bands.reduce((acc, b) => acc + b.order_count, 0))}</strong></span>
        </div>
      )}
    </div>
  );
});

DiscountProfitWidget.displayName = 'DiscountProfitWidget';

export default DiscountProfitWidget;
