import React, { useEffect, useState } from 'react';
import { Clock, CheckCircle2, AlertTriangle, RefreshCw, Inbox } from 'lucide-react';
import { historyService } from '@/services/historyService';
import { SmbHistoryItem } from '@/types/history';

export const SubmissionHistory: React.FC = () => {
  const [history, setHistory] = useState<SmbHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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
    switch (status) {
      case 'Ready':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            Ready
          </span>
        );
      case 'Needs attention — please resend':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            Needs attention — please resend
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-300 dark:border-blue-800">
            <Clock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 animate-spin" />
            Processing
          </span>
        );
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Submission History</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track the status of your data submissions and processing readiness.
          </p>
        </div>
        <button
          onClick={fetchHistory}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-750 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="bg-white dark:bg-gray-850 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500 dark:text-gray-400">
            <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-3 text-blue-600" />
            Loading submissions...
          </div>
        ) : history.length === 0 ? (
          <div className="p-16 text-center">
            <Inbox className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">No submissions yet</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Your ingested files and data transmissions will appear here once submitted.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
                  <th className="py-3.5 px-6">Submission Date</th>
                  <th className="py-3.5 px-6">Event</th>
                  <th className="py-3.5 px-6 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 text-sm">
                {history.map((item) => (
                  <tr
                    key={item.batch_id}
                    className="hover:bg-gray-50/60 dark:hover:bg-gray-800/40 transition-colors"
                  >
                    <td className="py-4 px-6 text-gray-900 dark:text-gray-100 font-medium">
                      {item.date || '—'}
                    </td>
                    <td className="py-4 px-6 text-gray-600 dark:text-gray-300">
                      {item.label || 'Data received'}
                    </td>
                    <td className="py-4 px-6 text-right">
                      {renderStatusBadge(item.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubmissionHistory;
