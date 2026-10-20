import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { ChartDataPoint } from '@/types/data';
import { useTheme } from '@/hooks/useTheme';
import { formatINR, formatINRCompact } from '@/utils/currency';

interface LineChartCardProps {
  title: string;
  subtitle?: string;
  data: ChartDataPoint[];
  className?: string;
}

export const LineChartCard: React.FC<LineChartCardProps> = ({
  title,
  subtitle,
  data,
  className = '',
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const gridColor = isDark ? '#262626' : '#E5E7EB';
  const textColor = isDark ? '#A3A3A3' : '#6B7280';
  const tooltipBg = isDark ? '#161616' : '#FFFFFF';
  const tooltipBorder = isDark ? '#262626' : '#E5E7EB';

  return (
    <div
      className={`p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark ${className}`}
    >
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="4 4" stroke={gridColor} vertical={false} />
            <XAxis
              dataKey="date"
              stroke={textColor}
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke={textColor}
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => formatINRCompact(v)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderRadius: '8px',
                color: isDark ? '#F5F5F5' : '#111827',
                fontSize: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
              formatter={(value: any, name: string) => [
                name === 'Revenue' ? formatINR(Number(value)) : value,
                name,
              ]}
            />
            <Legend
              wrapperStyle={{
                fontSize: '12px',
                paddingTop: '16px',
                color: textColor,
              }}
            />
            <Line
              type="monotone"
              dataKey="revenue"
              name="Revenue"
              stroke="#3B82F6"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#3B82F6' }}
              activeDot={{ r: 6, fill: '#3B82F6', stroke: isDark ? '#161616' : '#FFFFFF', strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="orders"
              name="Orders"
              stroke="#10B981"
              strokeWidth={2}
              strokeDasharray="3 3"
              dot={{ r: 2.5, fill: '#10B981' }}
              activeDot={{ r: 5, fill: '#10B981' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
