import React from 'react';
import {
  DollarSign,
  TrendingUp,
  Users,
  Activity,
  Database,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { KPIMetric } from '@/types/data';

interface KPICardProps {
  metric: KPIMetric;
  className?: string;
}

const iconMap = {
  dollar: DollarSign,
  chart: TrendingUp,
  users: Users,
  activity: Activity,
  database: Database,
  shield: ShieldCheck,
};

export const KPICard: React.FC<KPICardProps> = ({ metric, className = '' }) => {
  const IconComponent = iconMap[metric.iconName] || Activity;

  return (
    <div
      className={`p-5 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark transition-all duration-200 hover:shadow-soft ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          {metric.label}
        </span>
        <div className="p-2 rounded-control bg-black/5 dark:bg-white/5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          <IconComponent className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-3">
        <div className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
          {metric.value}
        </div>
        <div
          className={`flex items-center text-xs font-medium ${
            metric.isPositive ? 'text-helios-accent-teal' : 'text-helios-error'
          }`}
        >
          {metric.isPositive ? (
            <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
          ) : (
            <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
          )}
          <span>{Math.abs(metric.delta)}%</span>
        </div>
      </div>

      <div className="mt-2 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
        vs. {metric.timeframe}
      </div>
    </div>
  );
};
