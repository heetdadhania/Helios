import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  Eye,
  RefreshCw,
  Search,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';
import { oversightService } from '@/services/oversightService';
import { TenantHealthItem, TenantHealthListResponse, HealthStatusType } from '@/types/oversight';
import { formatCountIN } from '@/utils/currency';

export const TenantHealth: React.FC = () => {
  const navigate = useNavigate();

  const [healthData, setHealthData] = useState<TenantHealthListResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | HealthStatusType>('all');
  const [selectedTenantIssues, setSelectedTenantIssues] = useState<TenantHealthItem | null>(null);

  const fetchHealth = async (isBackground: boolean = false) => {
    if (isBackground) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const data = await oversightService.getTenantHealth();
      setHealthData(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to evaluate organization health telemetry.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const filteredTenants = useMemo(() => {
    if (!healthData || !Array.isArray(healthData.tenants)) return [];
    return healthData.tenants.filter((tenant) => {
      const name = tenant.tenant_name || '';
      const slug = tenant.slug || '';
      const idStr = String(tenant.tenant_id ?? '');
      const matchesSearch =
        !searchQuery ||
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
        idStr.includes(searchQuery);

      const status = tenant.health_status || 'good';
      const matchesStatus =
        statusFilter === 'all' || status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [healthData, searchQuery, statusFilter]);

  const renderHealthBadge = (
    status?: HealthStatusType | string | null,
    issues: string[] = [],
    totalShipments: number = 0,
    pipelineStatus?: string | null
  ) => {
    const issueList = issues || [];
    const isZeroData = (totalShipments === 0 || totalShipments === null || totalShipments === undefined) && !pipelineStatus;

    switch (status) {
      case 'critical':
        return (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 shadow-sm"
            title={issueList.length > 0 ? issueList.join('; ') : 'Critical health status'}
          >
            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Critical</span>
          </span>
        );
      case 'needs_attention':
        return (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shadow-sm"
            title={issueList.length > 0 ? issueList.join('; ') : 'Needs attention'}
          >
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Needs Attention</span>
          </span>
        );
      case 'good':
      default:
        return (
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shadow-sm"
            title={isZeroData ? 'Nominal default standing (no telemetry recorded yet)' : 'Operating normally within SLA thresholds'}
          >
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{isZeroData ? 'Good (No Data)' : 'Good'}</span>
          </span>
        );
    }
  };

  const renderPipelineBadge = (status: string | null) => {
    if (!status) {
      return (
        <span className="text-xs text-slate-400 italic">No runs yet</span>
      );
    }
    const norm = status.toLowerCase();
    if (norm.includes('success')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" />
          <span>Success</span>
        </span>
      );
    }
    if (norm.includes('fail') || norm.includes('error')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
          <AlertCircle className="w-3 h-3" />
          <span>Failed</span>
        </span>
      );
    }
    if (norm.includes('running') || norm.includes('process')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
          <RefreshCw className="w-3 h-3 animate-spin" />
          <span>Running</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20 capitalize">
        {status.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
            <Activity className="w-6 h-6 text-helios-accent-blue" />
            <span>Organization Health & SLA Oversight</span>
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Proactive health scoring based on latest pipeline completions, SLA breach thresholds, and delivery delays.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchHealth(true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-helios-accent-blue' : ''}`}
            />
            <span>Refresh Health</span>
          </button>

          <Link
            to="/admin/oversight/compare"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-accent-blue text-white hover:bg-helios-accent-blue/90 shadow-sm transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Compare Organizations</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Total Tenants */}
        <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Monitored</span>
            <Building2 className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {healthData?.total_tenants ?? '—'}
            </span>
            <span className="text-xs text-slate-400 font-medium">organizations</span>
          </div>
        </div>

        {/* Good Status */}
        <div
          onClick={() => setStatusFilter(statusFilter === 'good' ? 'all' : 'good')}
          className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border transition-all cursor-pointer ${
            statusFilter === 'good'
              ? 'border-emerald-500 ring-2 ring-emerald-500/20 shadow-md'
              : 'border-helios-border-light dark:border-helios-border-dark hover:border-emerald-500/50'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Good Standing</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              {healthData?.good_count ?? '—'}
            </span>
            <span className="text-xs text-slate-400">healthy</span>
          </div>
        </div>

        {/* Needs Attention */}
        <div
          onClick={() =>
            setStatusFilter(statusFilter === 'needs_attention' ? 'all' : 'needs_attention')
          }
          className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border transition-all cursor-pointer ${
            statusFilter === 'needs_attention'
              ? 'border-amber-500 ring-2 ring-amber-500/20 shadow-md'
              : 'border-helios-border-light dark:border-helios-border-dark hover:border-amber-500/50'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Needs Attention</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-amber-600 dark:text-amber-400">
              {healthData?.needs_attention_count ?? '—'}
            </span>
            <span className="text-xs text-slate-400">warning</span>
          </div>
        </div>

        {/* Critical */}
        <div
          onClick={() =>
            setStatusFilter(statusFilter === 'critical' ? 'all' : 'critical')
          }
          className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border transition-all cursor-pointer ${
            statusFilter === 'critical'
              ? 'border-rose-500 ring-2 ring-rose-500/20 shadow-md'
              : 'border-helios-border-light dark:border-helios-border-dark hover:border-rose-500/50'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-rose-600 dark:text-rose-400">Critical Breach</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-rose-600 dark:text-rose-400">
              {healthData?.critical_count ?? '—'}
            </span>
            <span className="text-xs text-slate-400">urgent</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search organization name, slug, or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>

        {/* Status Filter Buttons */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto overflow-x-auto w-full sm:w-auto">
          {(
            [
              { key: 'all', label: 'All Organizations' },
              { key: 'good', label: 'Good' },
              { key: 'needs_attention', label: 'Needs Attention' },
              { key: 'critical', label: 'Critical' },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                statusFilter === tab.key
                  ? 'bg-helios-accent-blue text-white shadow-sm'
                  : 'bg-black/5 dark:bg-white/5 text-slate-500 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table */}
      <div className="rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-helios-accent-blue mb-3" />
            <p className="text-xs text-slate-500 font-medium">Evaluating organization SLA & pipeline metrics...</p>
          </div>
        ) : filteredTenants.length === 0 ? (
          <div className="p-12 text-center">
            <Building2 className="w-10 h-10 mx-auto text-slate-400 mb-2 opacity-60" />
            <p className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No organizations match your search criteria
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting your search query or status filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-slate-400 uppercase font-semibold text-[11px] tracking-wider">
                  <th className="py-3 px-4">Organization</th>
                  <th className="py-3 px-4">Tier</th>
                  <th className="py-3 px-4">Health Status</th>
                  <th className="py-3 px-4">Latest Pipeline</th>
                  <th className="py-3 px-4">Late Delivery Rate</th>
                  <th className="py-3 px-4">Shipments</th>
                  <th className="py-3 px-4">Identified Issues</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                {filteredTenants.map((t) => (
                  <tr
                    key={t.tenant_id}
                    className="hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
                  >
                    {/* Organization */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-helios-accent-blue/10 flex items-center justify-center flex-shrink-0 text-helios-accent-blue font-bold text-xs">
                          {(t.tenant_name || 'T').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                            {t.tenant_name || `Organization #${t.tenant_id}`}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            {t.slug || `tenant-${t.tenant_id}`} • ID #{t.tenant_id}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Tier */}
                    <td className="py-3.5 px-4">
                      <span className="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-black/5 dark:bg-white/5 text-slate-600 dark:text-slate-300 border border-helios-border-light dark:border-helios-border-dark">
                        {t.tier || 'starter'}
                      </span>
                    </td>

                    {/* Health Status */}
                    <td className="py-3.5 px-4">
                      {renderHealthBadge(t.health_status, t.issues, t.total_shipments, t.latest_pipeline_status)}
                    </td>

                    {/* Latest Pipeline */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <div>{renderPipelineBadge(t.latest_pipeline_status)}</div>
                        {t.latest_batch_id && (
                          <div className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]">
                            {t.latest_batch_id}
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Late Delivery Rate */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        {(t.total_shipments ?? 0) === 0 ? (
                          <span className="text-slate-400 font-mono text-xs">0.0%</span>
                        ) : (
                          <span
                            className={`font-semibold ${
                              (t.late_delivery_rate_pct ?? 0) >= 25
                                ? 'text-rose-600 dark:text-rose-400 font-bold'
                                : (t.late_delivery_rate_pct ?? 0) >= 10
                                ? 'text-amber-600 dark:text-amber-400 font-semibold'
                                : 'text-helios-text-primary-light dark:text-helios-text-primary-dark'
                            }`}
                          >
                            {(t.late_delivery_rate_pct ?? 0).toFixed(1)}%
                          </span>
                        )}
                        {(t.total_shipments ?? 0) > 0 && (t.late_delivery_rate_pct ?? 0) >= 25 ? (
                          <TrendingUp className="w-3.5 h-3.5 text-rose-500" />
                        ) : (t.total_shipments ?? 0) > 0 && (t.late_delivery_rate_pct ?? 0) === 0 ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        ) : null}
                      </div>
                    </td>

                    {/* Total Shipments */}
                    <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300 font-mono">
                      {formatCountIN(t.total_shipments ?? 0)}
                    </td>

                    {/* Issues Breakdown */}
                    <td className="py-3.5 px-4 max-w-[200px]">
                      {(t.issues ?? []).length === 0 ? (
                        <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Nominal
                        </span>
                      ) : (
                        <div className="space-y-0.5">
                          {(t.issues ?? []).slice(0, 1).map((issue, idx) => (
                            <div
                              key={idx}
                              className="text-[11px] text-slate-600 dark:text-slate-300 truncate"
                              title={issue}
                            >
                              • {issue}
                            </div>
                          ))}
                          {(t.issues ?? []).length > 1 && (
                            <button
                              type="button"
                              onClick={() => setSelectedTenantIssues(t)}
                              className="text-[10px] text-helios-accent-blue hover:underline font-semibold"
                            >
                              +{(t.issues ?? []).length - 1} more issue{(t.issues ?? []).length > 2 ? 's' : ''}
                            </button>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => navigate(`/admin/oversight/dashboard/${t.tenant_id}`)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-helios-accent-blue/10 hover:bg-helios-accent-blue/20 text-helios-accent-blue border border-helios-accent-blue/20 transition-colors"
                          title="View-As organization dashboard"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Dashboard</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Issues Detail Modal */}
      {selectedTenantIssues && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Health Diagnostic: {selectedTenantIssues.tenant_name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTenantIssues(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-slate-400">
                The following operational flags were triggered by our automated health rules:
              </div>

              <div className="space-y-2">
                {selectedTenantIssues.issues.map((issue, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-xs flex items-start gap-2"
                  >
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-500" />
                    <span>{issue}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSelectedTenantIssues(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-black/5 dark:bg-white/5 text-slate-400 hover:text-white"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  const id = selectedTenantIssues.tenant_id;
                  setSelectedTenantIssues(null);
                  navigate(`/admin/oversight/dashboard/${id}`);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-helios-accent-blue text-white"
              >
                Open Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TenantHealth;
