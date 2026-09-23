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
import { ShippingModeComparisonResponse } from '@/types/dashboard';
import { useTheme } from '@/hooks/useTheme';
import { Navigation } from 'lucide-react';

interface ShippingModeWidgetProps {
  data: ShippingModeComparisonResponse | null;
  isLoading?: boolean;
  className?: string;
}

export const ShippingModeWidget: React.FC<ShippingModeWidgetProps> = ({
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

  const modes = data?.modes || [];
  const hasData = modes.length > 0;

  return (
    <div className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col justify-between ${className}`}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-sky-500" />
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Shipping Mode Velocity & Reliability
            </h3>
          </div>
          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-slate-400">
            Carrier Modes
          </span>
        </div>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-4">
          Transit duration and on-time performance joined with <code className="font-mono text-helios-accent-blue">gold.dim_shipping_mode</code>
        </p>

        {!hasData ? (
          <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl text-center p-6">
            <Navigation className="w-8 h-8 text-slate-400 mb-2" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No shipping carrier records
            </h4>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Fulfillment records are required to compare transit speeds across carriers.
            </p>
          </div>
        ) : (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modes} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis dataKey="mode_name" stroke={textColor} fontSize={11} tickLine={false} axisLine={false} />
                <YAxis
                  yAxisId="left"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}d`}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}%`}
                  domain={[80, 100]}
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
                    name.includes('Days') ? `${val} days` : `${val}%`,
                    name,
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar yAxisId="left" dataKey="avg_shipping_days" name="Avg Transit (Days)" fill="#0284C7" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="right" dataKey="on_time_rate_pct" name="On-Time Rate (%)" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {hasData && (
        <div className="mt-4 pt-3 border-t border-helios-border-light dark:border-helios-border-dark flex items-center justify-between text-[11px] text-slate-400">
          <span>Fastest: <strong className="font-mono text-helios-accent-teal">{modes.reduce((min, m) => m.avg_shipping_days < min.avg_shipping_days ? m : min, modes[0]).mode_name}</strong></span>
          <span>Highest On-Time: <strong className="font-mono text-emerald-600">{modes.reduce((max, m) => m.on_time_rate_pct > max.on_time_rate_pct ? m : max, modes[0]).mode_name}</strong></span>
        </div>
      )}
    </div>
  );
};

export default ShippingModeWidget;
