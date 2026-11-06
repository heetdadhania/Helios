import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import { RevenueBySegmentResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Users2 } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface CustomerSegmentWidgetProps {
  data: RevenueBySegmentResponse | null;
  isLoading?: boolean;
  className?: string;
}

const SEGMENT_COLORS = [
  '#0EA5E9', // Sky blue (Consumer)
  '#8B5CF6', // Purple (Corporate)
  '#10B981', // Emerald (Home Office)
  '#F59E0B', // Amber
  '#EC4899', // Pink
];

export const CustomerSegmentWidget: React.FC<CustomerSegmentWidgetProps> = React.memo(({
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
        <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-3 w-64 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const segments = data?.segments || [];
  const hasData = segments.length > 0;

  const chartData = useMemo(
    () =>
      segments.map((s) => ({
        name: s.segment,
        value: typeof s.revenue === 'string' ? parseFloat(s.revenue) : s.revenue,
        percentage: s.percentage,
        orderCount: s.order_count,
      })),
    [segments]
  );

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Users2 className="w-5 h-5 text-sky-500" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Revenue by Customer Segment
            </h3>
          </div>
          {data?.total_revenue !== undefined && hasData && (
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
              Total: {formatINRCompact(data.total_revenue)}
            </span>
          )}
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Market segment share joined across <code className="font-mono text-helios-accent-blue">gold.fact_orders</code> and <code className="font-mono text-helios-accent-blue">dim_customer</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Users2 className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No customer segment records
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Customer profile classifications will appear here once orders are processed.
            </p>
          </div>
        ) : (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                >
                  {chartData.map((_entry, index) => (
                    <Cell
                      key={`segment-cell-${index}`}
                      fill={SEGMENT_COLORS[index % SEGMENT_COLORS.length]}
                      stroke={isDark ? '#161616' : '#FFFFFF'}
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: tooltipBg,
                    borderColor: tooltipBorder,
                    borderRadius: '10px',
                    color: isDark ? '#F5F5F5' : '#111827',
                    fontSize: '12px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                  }}
                  formatter={(val: any, name: string, props: any) => [
                    `${formatINR(Number(val))} (${props.payload.percentage}% • ${formatCountIN(props.payload.orderCount)} orders)`,
                    name,
                  ]}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value) => {
                    const item = chartData.find((d) => d.name === value);
                    return (
                      <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-medium mr-3">
                        {value} ({item?.percentage || 0}%)
                      </span>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Segment Breakdown Footnotes */}
      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
          {segments.map((item, idx) => (
            <div key={item.segment} className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-2 truncate">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: SEGMENT_COLORS[idx % SEGMENT_COLORS.length] }}
                />
                <span className="font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {item.segment}
                </span>
                <span className="text-slate-400 text-[10px]">
                  ({item.percentage}%)
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-slate-400">
                  {formatCountIN(item.order_count)} orders
                </span>
                <span className="font-mono font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatINR(item.revenue)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

CustomerSegmentWidget.displayName = 'CustomerSegmentWidget';

export default CustomerSegmentWidget;
