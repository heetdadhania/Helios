import React, { useEffect, useState, useMemo } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  Building2,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { DataQualityLogItem, Tenant } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { Pagination } from '@/components/ui/Pagination';

export const DataQualityLog: React.FC = () => {
  const [logs, setLogs] = useState<DataQualityLogItem[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedLog, setSelectedLog] = useState<DataQualityLogItem | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 15;

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [logsData, tenantsData] = await Promise.all([
        adminService.getDataQualityLogs(),
        adminService.getTenants(),
      ]);
      setLogs(logsData);
      setTenants(tenantsData);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load data quality logs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedTenant, searchQuery]);

  const filteredLogs = useMemo(() => {
    return logs.filter((item) => {
      const matchesTenant =
        selectedTenant === 'all' ||
        item.tenant_id === selectedTenant ||
        item.tenant_name.toLowerCase() === selectedTenant.toLowerCase();

      const matchesSearch =
        searchQuery === '' ||
        item.batch_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.table_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.rejection_reason.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesTenant && matchesSearch;
    });
  }, [logs, selectedTenant, searchQuery]);

  const renderCategoryBadge = (category?: string) => {
    switch (category) {
      case 'Type Mismatch':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Type Mismatch
          </span>
        );
      case 'Schema Drift':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            Schema Drift
          </span>
        );
      case 'Null Threshold Exceeded':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            Null SLA Breach
          </span>
        );
      case 'Duplicate Key':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            Duplicate Key
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-500/10 text-slate-400">
            Validation Error
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Data Quality & Rejection Audit Log
          </h1>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Audit trail of rejected records, null threshold breaches, and schema inconsistencies quarantined during Bronze to Silver ingestion.
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-helios-accent-blue' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter by Tenant and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Batch ID, table name, or rejection reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>

        {/* Organization Filter Dropdown */}
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-400">Filter by Organization:</span>
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          >
            <option value="all">All Organizations</option>
            {tenants.map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Data Quality Log Table */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : error ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Failed to Load Data Quality Logs
            </h3>
            <p className="text-xs text-rose-600 dark:text-rose-400 max-w-sm mx-auto">
              {error}
            </p>
            <button
              type="button"
              onClick={loadData}
              className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No Data Quality Violations
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              All processed rows for the selected organization filter meet strict Medallion lakehouse quality thresholds.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                  <th className="py-3 px-4 font-semibold">Batch ID</th>
                  <th className="py-3 px-4 font-semibold">Organization</th>
                  <th className="py-3 px-4 font-semibold">Table Name</th>
                  <th className="py-3 px-4 font-semibold">Category</th>
                  <th className="py-3 px-4 font-semibold">Rejection Reason</th>
                  <th className="py-3 px-4 font-semibold">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {filteredLogs
                  .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                  .map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-helios-accent-blue whitespace-nowrap">
                      {log.batch_id}
                    </td>
                    <td className="py-3.5 px-4 font-medium whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>{log.tenant_name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-slate-300 whitespace-nowrap">
                      {log.table_name}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderCategoryBadge(log.error_category)}
                    </td>
                    <td className="py-3.5 px-4 max-w-md">
                      <div className="truncate text-rose-600 dark:text-rose-400 font-mono text-[11px]" title={log.rejection_reason}>
                        {log.rejection_reason}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{new Date(log.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            currentPage={currentPage}
            totalItems={filteredLogs.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        </>
      )}
      </div>

      {/* Detail Modal for Selected Rejection */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Rejection Audit Detail
                  </h3>
                  <p className="text-[11px] text-slate-400">Batch {selectedLog.batch_id}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-black/10 dark:hover:bg-white/10"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-black/5 dark:bg-white/5 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-400">Organization:</span>
                  <span className="font-semibold">{selectedLog.tenant_name} (ID: {selectedLog.tenant_id})</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Delta Table:</span>
                  <span className="font-mono font-semibold text-helios-accent-blue">{selectedLog.table_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Timestamp:</span>
                  <span>{new Date(selectedLog.timestamp).toISOString()}</span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 font-semibold block mb-1">Quarantine Diagnostic:</span>
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 font-mono text-[11px] break-words">
                  {selectedLog.rejection_reason}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
              >
                Close Audit Detail
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataQualityLog;
