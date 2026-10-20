import React, { useState } from 'react';
import {
  Flag,
  AlertTriangle,
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import { supportService } from '@/services/supportService';
import { SupportMessage } from '@/types/support';

interface FlagForAdminButtonProps {
  tenantId: number | string;
  batchId?: string | null;
  tenantName?: string | null;
  variant?: 'button' | 'compact' | 'warning' | 'link';
  label?: string;
  className?: string;
  onSuccess?: (message: SupportMessage) => void;
}

export const FlagForAdminButton: React.FC<FlagForAdminButtonProps> = ({
  tenantId,
  batchId,
  tenantName,
  variant = 'warning',
  label = 'Flag for Admin',
  className = '',
  onSuccess,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ show: boolean; text: string }>({
    show: false,
    text: '',
  });

  const handleOpen = () => {
    setMessage('');
    setError(null);
    setIsOpen(true);
  };

  const handleClose = () => {
    if (!sending) {
      setIsOpen(false);
      setMessage('');
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) {
      setError('Please provide a brief reason or explanation before submitting.');
      return;
    }

    setSending(true);
    setError(null);

    try {
      const result = await supportService.flagForAdmin({
        tenant_id: Number(tenantId) || 1,
        batch_id: batchId || undefined,
        message: message.trim(),
      });

      setIsOpen(false);
      setMessage('');
      setToast({
        show: true,
        text: 'Escalation submitted to Admin inbox ✓',
      });
      if (onSuccess) {
        onSuccess(result);
      }
      setTimeout(() => {
        setToast({ show: false, text: '' });
      }, 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to submit escalation. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const renderTrigger = () => {
    switch (variant) {
      case 'compact':
        return (
          <button
            type="button"
            onClick={handleOpen}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-colors shadow-xs ${className}`}
            title="Escalate issue directly to an Administrator"
          >
            <Flag className="w-3 h-3 text-rose-500 fill-current" />
            <span>{label}</span>
          </button>
        );
      case 'link':
        return (
          <button
            type="button"
            onClick={handleOpen}
            className={`inline-flex items-center gap-1 text-xs font-semibold text-rose-600 dark:text-rose-400 hover:underline transition-colors ${className}`}
            title="Escalate issue directly to an Administrator"
          >
            <Flag className="w-3.5 h-3.5 fill-current" />
            <span>{label}</span>
          </button>
        );
      case 'button':
        return (
          <button
            type="button"
            onClick={handleOpen}
            className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-800 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition shadow-xs ${className}`}
            title="Escalate issue directly to an Administrator"
          >
            <Flag className="w-3.5 h-3.5 text-rose-500 fill-current" />
            <span>{label}</span>
          </button>
        );
      case 'warning':
      default:
        return (
          <button
            type="button"
            onClick={handleOpen}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-lg border border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition shadow-xs ${className}`}
            title="Escalate issue directly to an Administrator"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            <span>{label}</span>
          </button>
        );
    }
  };

  return (
    <>
      {renderTrigger()}

      {/* Escalation Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl border border-rose-500/30 overflow-hidden animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between bg-rose-500/5">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-500">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Flag for Admin Escalation
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Direct operational dispatch to Platform Administrators
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleClose}
                disabled={sending}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Context Badge Row */}
            <div className="px-6 pt-4 pb-1 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold text-slate-500 dark:text-slate-400">Target Context:</span>
              <span className="font-semibold px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {tenantName || `Organization #${tenantId}`}
              </span>
              {batchId && (
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 font-semibold border border-rose-500/20">
                  Batch: {batchId}
                </span>
              )}
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSubmit} className="p-6 space-y-4 pt-3">
              <div>
                <label
                  htmlFor="admin-flag-reason"
                  className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
                >
                  Escalation Reason & Notes *
                </label>
                <textarea
                  id="admin-flag-reason"
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Detail the issue requiring Admin intervention (e.g. unknown data format, unresolvable quality rejections, upstream API failure, Databricks cluster timeout)..."
                  className="w-full text-xs p-3 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-800 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none font-sans"
                  required
                  autoFocus
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  This flag will appear in the Admin Support Inbox tagged as a Team Member escalation.
                </p>
              </div>

              {/* Error Banner */}
              {error && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center gap-2 text-rose-600 dark:text-rose-400 text-xs font-medium">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={sending}
                  className="px-4 py-2 text-xs font-semibold rounded-lg border border-helios-border-light dark:border-helios-border-dark text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sending || !message.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 transition shadow-sm"
                >
                  {sending ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Submitting Escalation...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Submit Escalation</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Toast */}
      {toast.show && (
        <div className="fixed bottom-6 right-6 z-50 p-4 rounded-xl bg-slate-900 dark:bg-neutral-800 text-white shadow-xl border border-slate-700 dark:border-neutral-700 flex items-center gap-2.5 text-xs font-semibold animate-in fade-in slide-in-from-bottom-2 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 dark:text-emerald-400 shrink-0" />
          <span>{toast.text}</span>
        </div>
      )}
    </>
  );
};

export default FlagForAdminButton;
