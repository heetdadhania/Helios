import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, RefreshCw, Inbox, Loader2 } from 'lucide-react';
import { historyService } from '@/services/historyService';
import { SmbHistoryItem } from '@/types/history';
import { Pagination } from '@/components/ui/Pagination';

export const SubmissionHistory: React.FC = () => {
  const [history, setHistory] = useState<SmbHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await historyService.getMyHistory();
      setHistory(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load submission history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const renderStatusBadge = (status: string) => {
    const s = (status || '').toLowerCase();
    if (s === 'ready' || s === 'completed' || s === 'success') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
          <span>Ready</span>
        </span>
      );
    }
    if (s.includes('attention') || s.includes('resend') || s === 'failed' || s === 'error') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
          <span>Needs attention — please resend</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
        <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />
        <span>Processing</span>
      </span>
    );
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Submission History
          </h1>
          <p className="text-xs sm:text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Track the status of your data submissions and processing readiness.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchHistory}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50 self-start sm:self-auto shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-helios-accent-blue' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs sm:text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
          <button onClick={fetchHistory} className="underline font-bold hover:text-rose-700">
            Retry
          </button>
        </div>
      )}

      {/* Content Container */}
      <div className="bg-helios-card-light dark:bg-helios-card-dark rounded-xl shadow-sm border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        {loading ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[560px]">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-xs uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                  <th className="py-3.5 px-6">Submission Date</th>
                  <th className="py-3.5 px-6">Event</th>
                  <th className="py-3.5 px-6 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                {[1, 2, 3, 4].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4 px-6">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-4 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-6 w-24 bg-slate-200 dark:bg-slate-800 rounded-full ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : history.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-12 h-12 rounded-2xl bg-black/5 dark:bg-white/5 flex items-center justify-center mx-auto mb-3 text-slate-400">
              <Inbox className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No submissions yet
            </h3>
            <p className="text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 max-w-sm mx-auto">
              Your ingested files and data transmissions will appear here once submitted.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[560px]">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-xs uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                    <th className="py-3.5 px-6">Submission Date</th>
                    <th className="py-3.5 px-6">Event</th>
                    <th className="py-3.5 px-6 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-sm">
                  {history
                    .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                    .map((item) => (
                      <tr
                        key={item.batch_id}
                        className="hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="py-4 px-6 text-helios-text-primary-light dark:text-helios-text-primary-dark font-medium whitespace-nowrap">
                          {item.date || '—'}
                        </td>
                        <td className="py-4 px-6 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          {item.label || 'Data received'}
                        </td>
                        <td className="py-4 px-6 text-right whitespace-nowrap">
                          {renderStatusBadge(item.status)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            <Pagination
              currentPage={currentPage}
              totalItems={history.length}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default SubmissionHistory;
