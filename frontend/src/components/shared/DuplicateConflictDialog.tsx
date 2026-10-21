import React, { useState } from 'react';
import {
  AlertTriangle,
  X,
  RotateCcw,
  CheckCircle2,
  Clock,
  User,
  Layers,
  FileSearch,
} from 'lucide-react';

export interface DuplicateConflictData {
  matched: string;
  submitted_by: string;
  submitted_at: string;
  batch_id: string;
  overlapping_rows: number;
  message?: string;
}

interface DuplicateConflictDialogProps {
  isOpen: boolean;
  conflictData: DuplicateConflictData | null;
  onClose: () => void;
  onOverride: (reason: string) => Promise<void> | void;
  isOverriding?: boolean;
}

export const DuplicateConflictDialog: React.FC<DuplicateConflictDialogProps> = ({
  isOpen,
  conflictData,
  onClose,
  onOverride,
  isOverriding = false,
}) => {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !conflictData) return null;

  const handleClose = () => {
    if (!isOverriding) {
      setReason('');
      setError(null);
      onClose();
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 5) {
      setError('Override reason must be at least 5 characters.');
      return;
    }
    setError(null);
    try {
      await onOverride(reason.trim());
      setReason('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Override failed. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl border border-amber-500/40 overflow-hidden animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between bg-amber-500/10">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Duplicate Submission Detected (409 Conflict)
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                This dataset matches existing records in the platform
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            disabled={isOverriding}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Conflict Details Grid */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-50 dark:bg-neutral-800/60 p-4 rounded-xl border border-helios-border-light dark:border-helios-border-dark">
            <div className="flex items-start gap-2">
              <FileSearch className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-400 block text-[11px]">Match Type</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {conflictData.matched}
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Layers className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-400 block text-[11px]">Overlapping Rows</span>
                <span className="font-semibold text-rose-600 dark:text-rose-400">
                  {conflictData.overlapping_rows} rows
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <User className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-400 block text-[11px]">Prior Submitter</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {conflictData.submitted_by}
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-400 block text-[11px]">Submitted At</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {conflictData.submitted_at}
                </span>
              </div>
            </div>

            <div className="sm:col-span-2 pt-1 border-t border-helios-border-light dark:border-helios-border-dark">
              <span className="text-slate-400 block text-[11px]">Prior Batch ID</span>
              <code className="text-[11px] font-mono text-helios-accent-blue break-all">
                {conflictData.batch_id}
              </code>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleConfirm} className="space-y-4">
            <div>
              <label
                htmlFor="duplicate-override-reason"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1"
              >
                Override Reason * (Minimum 5 characters)
              </label>
              <textarea
                id="duplicate-override-reason"
                rows={3}
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  if (error && e.target.value.trim().length >= 5) {
                    setError(null);
                  }
                }}
                placeholder="Explain why this duplicate submission should be accepted and re-processed..."
                className="w-full text-xs p-3 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-800 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none font-sans"
                required
                autoFocus
              />
              <div className="flex justify-between items-center text-[11px] mt-1 text-slate-400">
                <span>Required for audit trail accountability row in meta.audit_trail</span>
                <span className={reason.trim().length >= 5 ? 'text-emerald-500' : 'text-slate-400'}>
                  {reason.trim().length} / 5 chars min
                </span>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-medium">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleClose}
                disabled={isOverriding}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-helios-border-light dark:border-helios-border-dark text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                id="confirm-duplicate-override-btn"
                disabled={isOverriding || reason.trim().length < 5}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 transition shadow-sm"
              >
                {isOverriding ? (
                  <>
                    <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                    <span>Overriding...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Submit anyway</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default DuplicateConflictDialog;
