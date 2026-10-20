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
import { TopProductsResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Package, Award } from 'lucide-react';
import { formatINR, formatINRCompact, formatCountIN } from '@/utils/currency';

interface TopProductsWidgetProps {
  data: TopProductsResponse | null;
  isLoading?: boolean;
  className?: string;
}

const BAR_COLORS = ['#3B82F6', '#2563EB', '#1D4ED8', '#1E40AF', '#1E3A8A', '#0284C7', '#0369A1', '#075985'];

export const TopProductsWidget: React.FC<TopProductsWidgetProps> = React.memo(({
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
        <div className="h-5 w-40 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
        <div className="h-3 w-64 bg-slate-200 dark:bg-slate-800 rounded mb-6" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded" />
      </div>
    );
  }

  const products = data?.products || [];
  const hasData = products.length > 0;

  // Format data for horizontal bar display (take top 6 for clean visual fit)
  const chartItems = useMemo(
    () =>
      products.slice(0, 6).map((p) => ({
        name: p.product_name.length > 20 ? `${p.product_name.slice(0, 18)}...` : p.product_name,
        fullName: p.product_name,
        revenue: p.total_revenue,
        units: p.total_units_sold,
        orders: p.total_orders,
        category: p.category || 'General',
      })),
    [products]
  );

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-helios-accent-blue" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Top Selling Products
            </h3>
          </div>
          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-slate-400">
            Ranked by Revenue
          </span>
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Direct revenue leaders joined across <code className="font-mono text-helios-accent-blue">gold.fact_orders</code> and <code className="font-mono text-helios-accent-blue">dim_product</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Award className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No product sales recorded
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Connect a data source to generate product performance insights.
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
                    `${formatINR(Number(val))} (${formatCountIN(props.payload.units)} units)`,
                    props.payload.fullName,
                  ]}
                />
                <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                  {chartItems.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Top 3 Quick Stats List */}
      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
          {products.slice(0, 3).map((item, idx) => (
            <div key={item.product_id} className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-2 truncate">
                <span className="w-4 h-4 rounded-full bg-helios-accent-blue/10 text-helios-accent-blue font-bold flex items-center justify-center text-[10px]">
                  {idx + 1}
                </span>
                <span className="font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark truncate">
                  {item.product_name}
                </span>
              </div>
              <span className="font-mono font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark ml-2">
                {formatINR(item.total_revenue)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

TopProductsWidget.displayName = 'TopProductsWidget';

export default TopProductsWidget;
