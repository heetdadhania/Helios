import React, { useState, useEffect } from 'react';
import {
  Activity,
  ArrowRight,
  Database,
  Radio,
  UploadCloud,
} from 'lucide-react';
import { PipelineRun, IngestionSourceType } from '@/types/pipelineHealth';
import { StageStatusBadge } from '@/components/admin/StageStatusBadge';
import { Pagination } from '@/components/ui/Pagination';

export const SourceTypeIcon: React.FC<{ type: IngestionSourceType }> = ({ type }) => {
  const norm = (type || '').toLowerCase();
  if (norm === 'db_connection' || norm.includes('db')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
        <Database className="w-3 h-3 flex-shrink-0" />
        <span>DB Sync</span>
      </span>
    );
  }
  if (norm === 'api_push' || norm.includes('api')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
        <Radio className="w-3 h-3 flex-shrink-0" />
        <span>API Push</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
      <UploadCloud className="w-3 h-3 flex-shrink-0" />
      <span>File Upload</span>
    </span>
  );
};

export interface PipelineSectionProps {
  id: string;
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  count: number;
  variant: 'rose' | 'blue' | 'emerald' | 'amber' | 'slate';
  runs: PipelineRun[];
  isLoading: boolean;
  searchQuery?: string;
  emptyTitle: string;
  emptyDescription: string;
  emptyIcon?: React.ReactNode;
  onInspect: (batchId: string) => void;
}

export const PipelineSection: React.FC<PipelineSectionProps> = React.memo(({
  id,
  title,
  subtitle,
  icon,
  count,
  variant,
  runs,
  isLoading,
  searchQuery = '',
  emptyTitle,
  emptyDescription,
  emptyIcon,
  onInspect,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, runs.length]);
  const badgeClasses = {
    rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
  }[variant];

  const headerBorder = {
    rose: 'border-l-4 border-l-rose-500',
    blue: 'border-l-4 border-l-blue-500',
    emerald: 'border-l-4 border-l-emerald-500',
    amber: 'border-l-4 border-l-amber-500',
    slate: 'border-l-4 border-l-slate-400',
  }[variant];

  return (
    <div
      id={`section-${id}`}
      className={`rounded-xl overflow-hidden bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm transition-all ${headerBorder}`}
    >
      {/* Section Header */}
      <div className="p-4 sm:px-5 sm:py-3.5 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between gap-3 bg-black/[0.01] dark:bg-white/[0.01]">
        <div className="flex items-center gap-2.5">
          <div className="flex-shrink-0">{icon}</div>
          <div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <span>{title}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-mono font-semibold border ${badgeClasses}`}
              >
                {isLoading ? '...' : count}
              </span>
            </h3>
            {subtitle && (
              <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Content: Loading Skeleton, Empty State, or Table */}
      {isLoading ? (
        <div className="p-6">
          <div className="space-y-3">
            {[1, 2, 3].map((idx) => (
              <div
                key={idx}
                className="h-10 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse flex items-center justify-between px-4"
              >
                <div className="w-1/4 h-3.5 bg-black/10 dark:bg-white/10 rounded" />
                <div className="w-1/6 h-3.5 bg-black/10 dark:bg-white/10 rounded" />
                <div className="w-1/5 h-3.5 bg-black/10 dark:bg-white/10 rounded" />
                <div className="w-16 h-5 bg-black/10 dark:bg-white/10 rounded" />
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-slate-400 mt-4">
            Loading {title.toLowerCase()}...
          </p>
        </div>
      ) : runs.length === 0 ? (
        <div className="py-12 px-6 text-center">
          <div className="flex justify-center mb-3">
            {emptyIcon || (
              <div className="w-12 h-12 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center text-slate-400">
                <Activity className="w-6 h-6" />
              </div>
            )}
          </div>
          <h4 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            {searchQuery ? `No matching runs in ${title}` : emptyTitle}
          </h4>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 max-w-md mx-auto leading-relaxed">
            {searchQuery
              ? `No runs matched "${searchQuery}" in this section.`
              : emptyDescription}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider text-[11px]">
                <th className="py-2.5 px-4 font-semibold">Tenant</th>
                <th className="py-2.5 px-4 font-semibold">Source</th>
                <th className="py-2.5 px-4 font-semibold">Current / Stopped Stage</th>
                <th className="py-2.5 px-4 font-semibold">Status</th>
                <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                <th className="py-2.5 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
              {runs
                .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                .map((run) => {
                const isFailed = run.status.toLowerCase() === 'failed';
                return (
                  <tr
                    key={run.batch_id}
                    onClick={() => onInspect(run.batch_id)}
                    className={`hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer group ${
                      isFailed ? 'bg-rose-500/[0.02]' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      <div className="font-semibold text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {run.tenant || run.tenant_name || `Tenant ${run.tenant_id}`}
                      </div>
                      <div className="font-mono text-[10px] text-slate-400 truncate max-w-[150px]">
                        {run.batch_id}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <SourceTypeIcon type={run.source_type} />
                    </td>

                    <td className="py-3 px-4">
                      <StageStatusBadge
                        stage={run.current_stage}
                        status={run.status}
                      />
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark capitalize">
                        {run.status.replace(/_/g, ' ')}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark text-[11px]">
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '—'}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onInspect(run.batch_id);
                        }}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold transition-colors ${
                          isFailed
                            ? 'bg-rose-500/10 text-rose-600 hover:bg-rose-500/20'
                            : 'bg-black/5 dark:bg-white/5 text-slate-600 dark:text-slate-300 hover:bg-black/10'
                        }`}
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <Pagination
            currentPage={currentPage}
            totalItems={runs.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        </div>
      )}
    </div>
  );
});

PipelineSection.displayName = 'PipelineSection';
