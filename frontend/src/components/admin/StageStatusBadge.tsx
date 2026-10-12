import React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  Database,
  XCircle,
} from 'lucide-react';

interface StageStatusBadgeProps {
  stage?: string | null;
  status: string;
  className?: string;
}

const STAGE_LABELS: Record<string, string> = {
  bronze: 'Bronze',
  bronze_ingest: 'Bronze',
  received: 'Received',
  schema_inference: 'Schema Inference',
  awaiting_confirmation: 'Confirmation',
  silver: 'Silver',
  silver_clean: 'Silver',
  gold: 'Gold',
  gold_transform: 'Gold',
};

export const StageStatusBadge: React.FC<StageStatusBadgeProps> = ({
  stage,
  status,
  className = '',
}) => {
  const normStatus = (status || '').toLowerCase().trim();
  const normStage = (stage || '').toLowerCase().trim();
  const stageName = STAGE_LABELS[normStage] || normStage.replace(/_/g, ' ') || 'Pipeline';

  // Failed states
  if (normStatus === 'failed') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 ${className}`}
        title={`Execution halted at ${stageName}`}
      >
        <AlertCircle className="w-3.5 h-3.5 text-rose-500 flex-shrink-0 animate-pulse" />
        <span>Failed — {stageName}</span>
      </span>
    );
  }

  // Cancelled state
  if (normStatus === 'cancelled') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border border-zinc-500/20 ${className}`}
      >
        <XCircle className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
        <span>Cancelled</span>
      </span>
    );
  }

  // Rejected state
  if (normStatus === 'rejected') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 ${className}`}
      >
        <XCircle className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
        <span>Rejected</span>
      </span>
    );
  }

  // Stalled state
  if (normStatus === 'stalled') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 ${className}`}
        title="Execution stalled due to missing worker heartbeat"
      >
        <AlertTriangle className="w-3.5 h-3.5 text-orange-500 flex-shrink-0" />
        <span>Stalled</span>
      </span>
    );
  }

  // Restart Required
  if (normStatus === 'restart_required') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 ${className}`}
        title="Requires SMB Owner re-upload or re-sync"
      >
        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
        <span>Restart Required</span>
      </span>
    );
  }


  // Success state
  if (normStatus === 'success' || normStatus === 'completed') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 ${className}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
        <span>Success</span>
      </span>
    );
  }

  // Awaiting confirmation
  if (normStatus === 'awaiting_confirmation') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 ${className}`}
      >
        <Clock className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
        <span>Awaiting Confirmation</span>
      </span>
    );
  }

  // Ingested (Bronze complete)
  if (normStatus === 'ingested') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20 ${className}`}
      >
        <Database className="w-3.5 h-3.5 text-sky-500 flex-shrink-0" />
        <span>Ingested — Bronze</span>
      </span>
    );
  }

  // Running states (silver_running, gold_running, schema_inference_running, processing)
  if (normStatus.includes('running') || normStatus === 'processing' || normStatus === 'in_progress') {
    let runningLabel = `Running — ${stageName}`;
    if (normStatus === 'silver_running') runningLabel = 'Running — Silver';
    if (normStatus === 'gold_running') runningLabel = 'Running — Gold';
    if (normStatus === 'schema_inference_running') runningLabel = 'Running — Schema Inference';

    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 ${className}`}
      >
        <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />
        <span>{runningLabel}</span>
      </span>
    );
  }

  // Default badge
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20 ${className}`}
    >
      <Clock className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
      <span className="capitalize">{normStatus.replace(/_/g, ' ')}</span>
    </span>
  );
};
