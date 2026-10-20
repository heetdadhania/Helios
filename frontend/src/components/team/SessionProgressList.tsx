import React from 'react';
import {
  CheckCircle2,
  Clock,
  FileText,
  Database,
  ArrowRight,
  Trash2,
  Layers,
  Sparkles,
} from 'lucide-react';

export interface SessionProgressItem {
  id: string;
  tenantName: string;
  tenantId?: string | number;
  timestamp: string;
  status: string;
  details?: string;
  batchId?: string;
  uploadId?: number;
  type?: 'file' | 'database';
}

export interface SessionProgressListProps {
  items: SessionProgressItem[];
  title?: string;
  description?: string;
  onDone?: () => void;
  doneButtonLabel?: string;
  onClear?: () => void;
  className?: string;
}

export const SessionProgressList: React.FC<SessionProgressListProps> = ({
  items,
  title = 'Session Progress',
  description = 'Organization batches submitted during this active session',
  onDone,
  doneButtonLabel = 'Done for now',
  onClear,
  className = '',
}) => {
  return (
    <div
      className={`rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark p-5 shadow-sm space-y-4 ${className}`}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-helios-accent-teal/10 flex items-center justify-center text-helios-accent-teal">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {title}
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-helios-accent-teal/10 text-helios-accent-teal border border-helios-accent-teal/20">
                {items.length} {items.length === 1 ? 'batch' : 'batches'}
              </span>
            </div>
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
              {description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {items.length > 0 && onClear && (
            <button
              type="button"
              onClick={onClear}
              title="Clear session list"
              className="p-1.5 rounded text-xs text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          {onDone && (
            <button
              type="button"
              id="bulk-entry-done-btn"
              onClick={onDone}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-bold bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all hover:translate-x-0.5"
            >
              <span>{doneButtonLabel}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Item List or Empty State */}
      {items.length === 0 ? (
        <div className="text-center py-7 px-4 border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-control">
          <Clock className="w-8 h-8 text-slate-400 dark:text-slate-600 mx-auto mb-2 opacity-60" />
          <p className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            No submissions in this session yet
          </p>
          <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 max-w-sm mx-auto">
            Select an organization and submit ingestion above. Each completed submission will register
            here while resetting the form for the next organization.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
          {items.map((item, idx) => (
            <div
              key={item.id || idx}
              className="p-3 rounded-control bg-white dark:bg-neutral-900 border border-helios-border-light dark:border-helios-border-dark flex items-start justify-between gap-3 text-xs transition-colors hover:border-helios-accent-teal/40"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark truncate">
                      {item.tenantName}
                    </span>
                    {item.tenantId && (
                      <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-black/5 dark:bg-white/5 text-slate-500">
                        ID: {item.tenantId}
                      </span>
                    )}
                  </div>
                  {item.details && (
                    <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark truncate mt-0.5 flex items-center gap-1">
                      {item.type === 'database' ? (
                        <Database className="w-3 h-3 text-blue-500 shrink-0" />
                      ) : (
                        <FileText className="w-3 h-3 text-emerald-500 shrink-0" />
                      )}
                      <span className="font-mono">{item.details}</span>
                    </div>
                  )}
                  {item.batchId && (
                    <div className="font-mono text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 truncate">
                      Batch: {item.batchId.length > 20 ? `${item.batchId.substring(0, 18)}...` : item.batchId}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1 shrink-0">
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  {item.status}
                </span>
                <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                  <Clock className="w-2.5 h-2.5" />
                  {item.timestamp}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer Guidance */}
      {items.length > 0 && (
        <div className="pt-2 border-t border-helios-border-light dark:border-helios-border-dark flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-helios-accent-teal shrink-0" />
            <span>Ready for the next organization submission.</span>
          </span>
          {onDone && (
            <button
              type="button"
              onClick={onDone}
              className="text-xs font-semibold text-helios-accent-blue hover:underline"
            >
              Finish Session →
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default SessionProgressList;
