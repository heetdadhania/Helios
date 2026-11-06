import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Shield,
  Search,
  Filter,
  RefreshCw,
  Building2,
  Clock,
  Download,
  AlertTriangle,
  User,
  FileText,
  X,
  Copy,
  Check,
  Calendar,
} from 'lucide-react';
import { AuditLogItem } from '@/types/audit';
import { auditService } from '@/services/auditService';
import { oversightService } from '@/services/oversightService';
import { Pagination } from '@/components/ui/Pagination';
import { SortControl, SortOption } from '@/components/ui/SortControl';
import { usePaginatedData } from '@/hooks/usePaginatedData';
import { useOrganizations } from '@/hooks/useOrganizations';
import { formatDateTimeIN } from '@/utils/currency';

const AUDIT_SORT_OPTIONS: SortOption[] = [
  { value: 'time', label: 'Time' },
  { value: 'actor', label: 'Actor' },
  { value: 'action', label: 'Action' },
  { value: 'organization', label: 'Organization' },
];

export const AuditTrail: React.FC = () => {
  const { organizations: tenants } = useOrganizations();

  // Filter states
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [actorQuery, setActorQuery] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [organizationFilter, setOrganizationFilter] = useState<string>('all');

  // Modal inspection state
  const [selectedAuditItem, setSelectedAuditItem] = useState<AuditLogItem | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Export state
  const [searchParams] = useSearchParams();
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const sortBy = searchParams.get('sort_by') || '';
  const sortOrder = (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc';

  const {
    data: auditLogs,
    total,
    page,
    pageSize,
    isLoading,
    error,
    setPage,
    refetch,
  } = usePaginatedData<AuditLogItem>({
    fetchFn: (params) =>
      auditService.getAuditTrail(
        {
          start_date: params.start_date || undefined,
          end_date: params.end_date || undefined,
          actor: params.actor || undefined,
          action: params.action !== 'all' ? params.action : undefined,
          organization: params.organization !== 'all' ? params.organization : undefined,
        },
        params.page,
        params.pageSize,
        params.sortBy,
        params.sortOrder
      ),
    filters: {
      start_date: startDate,
      end_date: endDate,
      actor: actorQuery,
      action: actionFilter,
      organization: organizationFilter,
      sortBy,
      sortOrder,
    },
    pageSize: 20,
  });

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      await oversightService.downloadAuditExport(startDate || undefined, endDate || undefined);
    } catch (err: any) {
      setExportError(err?.response?.data?.detail || 'Failed to download audit export.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleCopyJson = (jsonStr: string) => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderActionBadge = (action: string) => {
    const act = (action || '').toLowerCase();
    let colorClasses = 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';

    if (act.includes('approved') || act.includes('created') || act.includes('reactivate')) {
      colorClasses = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
    } else if (act.includes('rejected') || act.includes('cancelled') || act.includes('deactivate') || act.includes('locked')) {
      colorClasses = 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
    } else if (act.includes('retry') || act.includes('restart') || act.includes('override')) {
      colorClasses = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
    } else if (act.includes('upload') || act.includes('profile') || act.includes('email') || act.includes('password') || act.includes('updated')) {
      colorClasses = 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
    }

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-medium border ${colorClasses}`}>
        {action}
      </span>
    );
  };

  const renderRoleBadge = (role?: string | null) => {
    const r = (role || 'system').toLowerCase();
    let badgeClass = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    if (r === 'admin') badgeClass = 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
    if (r === 'team_member') badgeClass = 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
    if (r === 'smb_owner') badgeClass = 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';

    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider ${badgeClass}`}>
        {r.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-helios-accent-blue" />
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
              System Audit Trail
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Immutable administrative and operational audit records across authentication, organizations, workflows, and pipelines.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50 shadow-xs"
            title="Download unified system audit and event log CSV"
          >
            <Download className="w-3.5 h-3.5 text-helios-accent-blue" />
            <span>{isExporting ? 'Exporting...' : 'Export Audit Log'}</span>
          </button>
          <button
            type="button"
            onClick={refetch}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50 shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {exportError && (
        <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 rounded-xl">
          {exportError}
        </div>
      )}

      {/* Filter Controls Bar */}
      <div className="p-4 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Date Range Start */}
        <div>
          <label className="block text-[11px] font-medium text-slate-500 mb-1">Start Date</label>
          <div className="relative">
            <Calendar className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
        </div>

        {/* Date Range End */}
        <div>
          <label className="block text-[11px] font-medium text-slate-500 mb-1">End Date</label>
          <div className="relative">
            <Calendar className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
        </div>

        {/* Actor Search */}
        <div>
          <label className="block text-[11px] font-medium text-slate-500 mb-1">Actor (User ID, Name, Role)</label>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter by actor..."
              value={actorQuery}
              onChange={(e) => setActorQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
        </div>

        {/* Action Select */}
        <div>
          <label className="block text-[11px] font-medium text-slate-500 mb-1">Action</label>
          <div className="relative">
            <Filter className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            >
              <option value="all">All Actions</option>
              <option value="upload">Upload</option>
              <option value="batch_approved">Batch Approved</option>
              <option value="batch_rejected">Batch Rejected</option>
              <option value="batch_cancelled">Batch Cancelled</option>
              <option value="batch_retry">Batch Retry</option>
              <option value="batch_full_restart">Full Restart</option>
              <option value="duplicate_override">Duplicate Override</option>
              <option value="create_organization">Create Organization</option>
              <option value="create_team_member">Create Team Member</option>
              <option value="owner_updated">Owner Updated</option>
              <option value="owner_replaced">Owner Replaced</option>
              <option value="deactivate_owner">Deactivate Owner</option>
              <option value="reactivate_owner">Reactivate Owner</option>
              <option value="deactivate_team_member">Deactivate Team Member</option>
              <option value="reactivate_team_member">Reactivate Team Member</option>
              <option value="password_reset">Password Reset</option>
              <option value="profile_updated">Profile Updated</option>
              <option value="email_updated">Email Updated</option>
              <option value="password_changed">Password Changed</option>
              <option value="account_locked">Account Locked</option>
            </select>
          </div>
        </div>

        {/* Organization Select */}
        <div>
          <label className="block text-[11px] font-medium text-slate-500 mb-1">Organization</label>
          <div className="relative">
            <Building2 className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <select
              value={organizationFilter}
              onChange={(e) => setOrganizationFilter(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            >
              <option value="all">All Organizations</option>
              {tenants.map((t) => (
                <option key={t.tenant_id} value={String(t.tenant_id)}>
                  {t.business_name || t.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Audit Meta & Sort Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-1">
        <div className="text-xs text-slate-500">
          Total: <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{total}</span> immutable audit events
        </div>
        <SortControl options={AUDIT_SORT_OPTIONS} defaultSortOrder="desc" />
      </div>

      {/* Main Table Container */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : error ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Failed to Load Audit Trail
            </h3>
            <p className="text-xs text-rose-600 dark:text-rose-400 max-w-sm mx-auto">{error}</p>
            <button
              type="button"
              onClick={refetch}
              className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-slate-500/10 text-slate-400 flex items-center justify-center">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No Audit Records Found
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              No security or operational events match the selected criteria.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                    <th className="py-3 px-4 font-semibold">Timestamp</th>
                    <th className="py-3 px-4 font-semibold">Actor</th>
                    <th className="py-3 px-4 font-semibold">Action</th>
                    <th className="py-3 px-4 font-semibold">Organization</th>
                    <th className="py-3 px-4 font-semibold">Batch ID</th>
                    <th className="py-3 px-4 font-semibold">Reason</th>
                    <th className="py-3 px-4 font-semibold text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {auditLogs.map((item) => (
                    <tr
                      key={item.audit_id}
                      className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                    >
                      {/* Timestamp */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 dark:text-slate-400">
                        <div className="flex items-center gap-1.5 font-mono text-[11px]">
                          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{formatDateTimeIN(item.occurred_at)}</span>
                        </div>
                      </td>

                      {/* Actor */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-1.5 font-medium">
                            <User className="w-3.5 h-3.5 text-slate-400" />
                            <span>{item.actor_name || `User #${item.actor_user_id || 'System'}`}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            {renderRoleBadge(item.actor_role)}
                            {item.actor_email && (
                              <span className="text-[10px] text-slate-400">({item.actor_email})</span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {renderActionBadge(item.action)}
                      </td>

                      {/* Organization */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {item.tenant_name || item.tenant_id ? (
                          <div className="flex items-center gap-1.5 font-medium">
                            <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span>{item.tenant_name || `Organization #${item.tenant_id}`}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 font-mono text-[11px]">System</span>
                        )}
                      </td>

                      {/* Batch ID */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {item.batch_id ? (
                          <span className="font-mono text-[11px] text-helios-accent-blue truncate max-w-[120px] inline-block" title={item.batch_id}>
                            {item.batch_id.slice(0, 8)}...
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      {/* Reason */}
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="truncate text-slate-600 dark:text-slate-300" title={item.reason || ''}>
                          {item.reason || '—'}
                        </div>
                      </td>

                      {/* Details inspection */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        {item.details_json ? (
                          <button
                            type="button"
                            onClick={() => setSelectedAuditItem(item)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-accent-blue hover:bg-black/10 dark:hover:bg-white/10 transition-colors cursor-pointer"
                          >
                            <FileText className="w-3 h-3" />
                            <span>Payload</span>
                          </button>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              currentPage={page}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={setPage}
            />
          </>
        )}
      </div>

      {/* Structured Details JSON Inspection Modal */}
      {selectedAuditItem && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-helios-accent-blue" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Audit Event Details #{selectedAuditItem.audit_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedAuditItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-2 gap-2 p-3 bg-black/[0.02] dark:bg-white/[0.02] rounded-xl border border-helios-border-light dark:border-helios-border-dark font-mono text-[11px]">
                <div>
                  <span className="text-slate-400">Action: </span>
                  <span className="font-semibold">{selectedAuditItem.action}</span>
                </div>
                <div>
                  <span className="text-slate-400">Actor: </span>
                  <span>{selectedAuditItem.actor_name} ({selectedAuditItem.actor_role})</span>
                </div>
                <div>
                  <span className="text-slate-400">Time: </span>
                  <span>{formatDateTimeIN(selectedAuditItem.occurred_at)}</span>
                </div>
                <div>
                  <span className="text-slate-400">Organization: </span>
                  <span>{selectedAuditItem.tenant_name || selectedAuditItem.tenant_id || 'System'}</span>
                </div>
                {selectedAuditItem.batch_id && (
                  <div className="col-span-2">
                    <span className="text-slate-400">Batch ID: </span>
                    <span className="text-helios-accent-blue">{selectedAuditItem.batch_id}</span>
                  </div>
                )}
                {selectedAuditItem.reason && (
                  <div className="col-span-2">
                    <span className="text-slate-400">Reason: </span>
                    <span>{selectedAuditItem.reason}</span>
                  </div>
                )}
              </div>

              {selectedAuditItem.details_json && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-medium text-slate-400">Payload Diff / JSON:</span>
                    <button
                      type="button"
                      onClick={() => handleCopyJson(selectedAuditItem.details_json || '')}
                      className="inline-flex items-center gap-1 text-[11px] text-helios-accent-blue hover:underline"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                    </button>
                  </div>
                  <pre className="p-3 bg-black/5 dark:bg-white/5 rounded-xl border border-helios-border-light dark:border-helios-border-dark font-mono text-[11px] text-slate-800 dark:text-slate-200 overflow-x-auto max-h-60">
                    {(() => {
                      try {
                        return JSON.stringify(JSON.parse(selectedAuditItem.details_json), null, 2);
                      } catch {
                        return selectedAuditItem.details_json;
                      }
                    })()}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedAuditItem(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditTrail;
