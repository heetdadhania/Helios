import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
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
import { StageStatusBadge } from '@/components/admin/StageStatusBadge';

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
      setError(err?.message || 'Failed to load global submission audit log.');
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

  const renderSourceIcon = (sourceType: string) => {
    switch (sourceType?.toLowerCase()) {
      case 'db_connection':
        return <Database className="w-4 h-4 text-emerald-500" />;
      case 'api_push':
        return <Key className="w-4 h-4 text-amber-500" />;
      default:
        return <UploadCloud className="w-4 h-4 text-helios-accent-blue" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            System Submission History
          </h1>
          <p className="text-xs sm:text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Global audit log of all data transmissions and pipeline executions across all tenants.
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

      {/* Filter Toolbar */}
      <div className="bg-helios-card-light dark:bg-helios-card-dark p-4 rounded-xl shadow-sm border border-helios-border-light dark:border-helios-border-dark flex flex-col md:flex-row gap-4 justify-between items-center">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search tenant name or ID..."
            value={tenantFilter}
            onChange={(e) => setTenantFilter(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-bg-light dark:bg-helios-bg-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider">
              Status:
            </span>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-bg-light dark:bg-helios-bg-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
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
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs sm:text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Table Container */}
      <div className="bg-helios-card-light dark:bg-helios-card-dark rounded-xl shadow-sm border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        {loading ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[920px]">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-xs uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                  <th className="py-3.5 px-6">Tenant</th>
                  <th className="py-3.5 px-6">Source</th>
                  <th className="py-3.5 px-6">Stage</th>
                  <th className="py-3.5 px-6">Status</th>
                  <th className="py-3.5 px-6">Handled By</th>
                  <th className="py-3.5 px-6">Timestamp</th>
                  <th className="py-3.5 px-6 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                {[1, 2, 3, 4, 5].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4 px-6">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded mb-1" />
                      <div className="h-3 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-4 w-16 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-6 w-28 bg-slate-200 dark:bg-slate-800 rounded-full" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-6 w-20 bg-slate-200 dark:bg-slate-800 rounded-md" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="h-4 w-16 bg-slate-200 dark:bg-slate-800 rounded ml-auto" />
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
              Global tenant data submissions will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[920px]">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-xs uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                  <th className="py-3.5 px-6">Tenant</th>
                  <th className="py-3.5 px-6">Source</th>
                  <th className="py-3.5 px-6">Stage</th>
                  <th className="py-3.5 px-6">Status</th>
                  <th className="py-3.5 px-6">Handled By</th>
                  <th className="py-3.5 px-6">Timestamp</th>
                  <th className="py-3.5 px-6 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-sm">
                {history.map((item) => {
                  const isExpanded = expandedRows.has(item.batch_id);
                  const hasError = Boolean(item.error_message);

                  return (
                    <React.Fragment key={item.batch_id}>
                      <tr
                        onClick={() => hasError && toggleExpand(item.batch_id)}
                        className={`transition-colors ${
                          hasError
                            ? 'cursor-pointer hover:bg-black/[0.02] dark:hover:bg-white/[0.02]'
                            : 'hover:bg-black/[0.01] dark:hover:bg-white/[0.01]'
                        }`}
                      >
                        <td className="py-4 px-6 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          <div>{item.tenant}</div>
                          <div className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-normal">
                            Tenant #{item.tenant_id}
                          </div>
                        </td>
                        <td className="py-4 px-6 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          <div className="inline-flex items-center gap-1.5 capitalize text-xs">
                            {renderSourceIcon(item.source_type)}
                            <span>{item.source_type?.replace(/_/g, ' ')}</span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-mono text-xs">
                          {item.stage || '—'}
                        </td>
                        <td className="py-4 px-6">
                          <StageStatusBadge stage={item.stage} status={item.status} />
                        </td>
                        <td className="py-4 px-6">
                          {item.handled_by && item.handled_by !== 'N/A' ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                              <UserCheck className="w-3.5 h-3.5 text-blue-500" />
                              {item.handled_by}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">N/A</span>
                          )}
                        </td>
                        <td className="py-4 px-6 text-helios-text-secondary-light dark:text-helios-text-secondary-dark text-xs whitespace-nowrap">
                          {new Date(item.timestamp).toLocaleString()}
                        </td>
                        <td className="py-4 px-6 text-right whitespace-nowrap">
                          {hasError ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(item.batch_id);
                              }}
                              className="inline-flex items-center gap-1 text-xs text-rose-600 dark:text-rose-400 hover:underline font-semibold"
                            >
                              <span>Error Detail</span>
                              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Error Detail Row */}
                      {isExpanded && hasError && (
                        <tr className="bg-rose-500/[0.03] dark:bg-rose-950/20 border-b border-rose-500/20">
                          <td colSpan={7} className="p-4 px-6">
                            <div className="space-y-1.5">
                              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-semibold text-xs uppercase tracking-wider">
                                <AlertCircle className="w-4 h-4 text-rose-500" />
                                Failure Diagnostics & Error Trace
                              </div>
                              <pre className="mt-2 p-3 bg-helios-card-light dark:bg-neutral-900 border border-rose-500/20 rounded-lg text-xs font-mono text-rose-700 dark:text-rose-300 whitespace-pre-wrap break-all overflow-x-auto leading-relaxed">
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
