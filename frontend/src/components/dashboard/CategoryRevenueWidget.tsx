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
import { RevenueByCategoryResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Tag } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface CategoryRevenueWidgetProps {
  data: RevenueByCategoryResponse | null;
  isLoading?: boolean;
  className?: string;
}

const CATEGORY_COLORS = [
  '#6366F1', // Indigo
  '#3B82F6', // Blue
  '#06B6D4', // Cyan
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EC4899', // Pink
  '#8B5CF6', // Purple
  '#14B8A6', // Teal
];

export const CategoryRevenueWidget: React.FC<CategoryRevenueWidgetProps> = React.memo(({
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

  const categories = data?.categories || [];
  const hasData = categories.length > 0;

  const chartItems = useMemo(
    () =>
      categories.map((c) => ({
        name: c.category.length > 18 ? `${c.category.slice(0, 16)}...` : c.category,
        fullName: c.category,
        revenue: typeof c.revenue === 'string' ? parseFloat(c.revenue) : c.revenue,
        percentage: c.percentage,
        orderCount: c.order_count,
      })),
    [categories]
  );

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-indigo-500" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Revenue by Product Category
            </h3>
          </div>
          {data?.total_revenue !== undefined && hasData && (
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              Total: {formatINRCompact(data.total_revenue)}
            </span>
          )}
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Net revenue aggregated by catalog category in <code className="font-mono text-helios-accent-blue">gold.fact_orders</code> joined with <code className="font-mono text-helios-accent-blue">dim_product</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Tag className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No category revenue recorded
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Sales transactions mapped to catalog categories will appear here.
            </p>
          </div>
        ) : (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={chartItems}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} horizontal={false} />
                <XAxis
                  type="number"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => formatINRCompact(v)}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  width={110}
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
                  formatter={(val: any, _name: string, props: any) => [
                    `${formatINR(Number(val))} (${props.payload.percentage}% • ${formatCountIN(props.payload.orderCount)} orders)`,
                    props.payload.fullName,
                  ]}
                />
                <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                  {chartItems.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Quick Category Summary Breakdown */}
      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
          {categories.slice(0, 3).map((item, idx) => (
            <div key={item.category} className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-2 truncate">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: CATEGORY_COLORS[idx % CATEGORY_COLORS.length] }}
                />
                <span className="font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark truncate">
                  {item.category}
                </span>
                <span className="text-slate-400 text-[10px]">
                  ({item.percentage}%)
                </span>
              </div>
              <span className="font-mono font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark ml-2">
                {formatINR(item.revenue)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

CategoryRevenueWidget.displayName = 'CategoryRevenueWidget';

export default CategoryRevenueWidget;

