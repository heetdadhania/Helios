import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  ChevronDown,
  ChevronUp,
  Inbox,
  Database,
  UploadCloud,
  Key,
  UserCheck,
} from 'lucide-react';
import { historyService } from '@/services/historyService';
import { AdminHistoryItem } from '@/types/history';

export const AdminHistory: React.FC = () => {
  const [history, setHistory] = useState<AdminHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [tenantFilter, setTenantFilter] = useState<string>('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await historyService.getAdminHistory({
        status: statusFilter,
        tenant: tenantFilter,
      });
      setHistory(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load system-wide submission history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistory();
  };

  const toggleExpand = (batchId: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(batchId)) {
        next.delete(batchId);
      } else {
        next.add(batchId);
      }
      return next;
    });
  };

  const renderStatusBadge = (statusStr: string) => {
    const s = statusStr.toLowerCase();
    if (s === 'success' || s === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
          <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          Success
        </span>
      );
    }
    if (s === 'failed' || s === 'error') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
          <AlertCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
          Failed
        </span>
      );
    }
    if (s === 'awaiting_confirmation') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-950/50 dark:text-purple-300 border border-purple-300 dark:border-purple-800">
          <Clock className="w-3 h-3 text-purple-600 dark:text-purple-400" />
          Awaiting Review
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-300 dark:border-blue-800">
        <Clock className="w-3 h-3 text-blue-600 dark:text-blue-400 animate-spin" />
        {statusStr}
      </span>
    );
  };

  const renderSourceIcon = (sourceType: string) => {
    switch (sourceType?.toLowerCase()) {
      case 'db_connection':
        return <Database className="w-4 h-4 text-emerald-500" />;
      case 'api_push':
        return <Key className="w-4 h-4 text-amber-500" />;
      default:
        return <UploadCloud className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">System Submission History</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Global audit log of all data transmissions and pipeline executions across all tenants.
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

      {/* Filter Toolbar */}
      <div className="bg-white dark:bg-gray-850 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 flex flex-col md:flex-row gap-4 justify-between items-center">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search tenant name or ID..."
            value={tenantFilter}
            onChange={(e) => setTenantFilter(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Status:</span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="awaiting_confirmation">Awaiting Review</option>
            <option value="silver_running">Silver Running</option>
            <option value="gold_running">Gold Running</option>
            <option value="ingested">Ingested</option>
          </select>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-gray-850 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500 dark:text-gray-400">
            <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-3 text-blue-600" />
            Loading global submission audit...
          </div>
        ) : history.length === 0 ? (
          <div className="p-16 text-center">
            <Inbox className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">No submissions yet</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Global tenant data submissions will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
                  <th className="py-3.5 px-6">Tenant</th>
                  <th className="py-3.5 px-6">Source</th>
                  <th className="py-3.5 px-6">Stage</th>
                  <th className="py-3.5 px-6">Status</th>
                  <th className="py-3.5 px-6">Handled By</th>
                  <th className="py-3.5 px-6">Timestamp</th>
                  <th className="py-3.5 px-6 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 text-sm">
                {history.map((item) => {
                  const isExpanded = expandedRows.has(item.batch_id);
                  const hasError = Boolean(item.error_message);

                  return (
                    <React.Fragment key={item.batch_id}>
                      <tr
                        onClick={() => hasError && toggleExpand(item.batch_id)}
                        className={`transition-colors ${
                          hasError ? 'cursor-pointer hover:bg-gray-50/70 dark:hover:bg-gray-800/50' : ''
                        }`}
                      >
                        <td className="py-4 px-6 font-medium text-gray-900 dark:text-gray-100">
                          <div>{item.tenant}</div>
                          <div className="text-xs text-gray-400 font-normal">Tenant #{item.tenant_id}</div>
                        </td>
                        <td className="py-4 px-6 text-gray-600 dark:text-gray-300">
                          <div className="inline-flex items-center gap-1.5 capitalize">
                            {renderSourceIcon(item.source_type)}
                            <span>{item.source_type?.replace('_', ' ')}</span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-gray-600 dark:text-gray-300 font-mono text-xs">
                          {item.stage || '—'}
                        </td>
                        <td className="py-4 px-6">
                          {renderStatusBadge(item.status)}
                        </td>
                        <td className="py-4 px-6">
                          {item.handled_by && item.handled_by !== 'N/A' ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200 dark:border-blue-900/60">
                              <UserCheck className="w-3.5 h-3.5 text-blue-500" />
                              {item.handled_by}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="py-4 px-6 text-gray-500 dark:text-gray-400 text-xs">
                          {new Date(item.timestamp).toLocaleString()}
                        </td>
                        <td className="py-4 px-6 text-right">
                          {hasError ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(item.batch_id);
                              }}
                              className="inline-flex items-center gap-1 text-xs text-rose-600 dark:text-rose-400 hover:underline font-medium"
                            >
                              <span>Error Detail</span>
                              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            </button>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Error Detail Row */}
                      {isExpanded && hasError && (
                        <tr className="bg-rose-50/40 dark:bg-rose-950/20 border-b border-rose-100 dark:border-rose-900/40">
                          <td colSpan={7} className="p-4 px-6">
                            <div className="space-y-1">
                              <div className="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-semibold text-xs uppercase tracking-wider">
                                <AlertCircle className="w-4 h-4 text-rose-500" />
                                Failure Diagnostics & Error Stack
                              </div>
                              <pre className="mt-2 p-3 bg-white dark:bg-gray-900 border border-rose-200 dark:border-rose-900/60 rounded-lg text-xs font-mono text-rose-800 dark:text-rose-300 whitespace-pre-wrap break-all overflow-x-auto">
                                {item.error_message}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminHistory;
