import React, { useEffect, useState } from 'react';
import {
  Activity,
  ArrowDownToLine,
  Database,
  Download,
  FileSpreadsheet,
  Layers,
  RefreshCw,
  TrendingUp,
  Users,
  AlertCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { oversightService } from '@/services/oversightService';
import { PlatformUsageResponse } from '@/types/oversight';
import { useTheme } from '@/hooks/useTheme';

export const UsageDashboard: React.FC = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [usage, setUsage] = useState<PlatformUsageResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Audit Log Export modal state
  const [showExportModal, setShowExportModal] = useState<boolean>(false);
  const [exportStartDate, setExportStartDate] = useState<string>('');
  const [exportEndDate, setExportEndDate] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const fetchUsage = async (isBackground: boolean = false) => {
    if (isBackground) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);
    try {
      const data = await oversightService.getPlatformUsage();
      setUsage(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load platform usage telemetry.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, []);

  const handleExportAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsExporting(true);
    setExportError(null);
    try {
      await oversightService.downloadAuditExport(exportStartDate, exportEndDate);
      setShowExportModal(false);
      setExportStartDate('');
      setExportEndDate('');
    } catch (err: any) {
      setExportError(err?.message || 'Failed to download audit log export.');
    } finally {
      setIsExporting(false);
    }
  };

  const gridColor = isDark ? '#262626' : '#E5E7EB';
  const textColor = isDark ? '#A3A3A3' : '#6B7280';
  const tooltipBg = isDark ? '#161616' : '#FFFFFF';
  const tooltipBorder = isDark ? '#262626' : '#E5E7EB';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-helios-accent-blue" />
            <span>Platform Usage & Ingestion Telemetry</span>
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            System-wide ingestion throughput, ETL execution health, and pipeline run trends over time.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchUsage(true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-helios-accent-blue' : ''}`}
            />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setShowExportModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-accent-blue text-white hover:bg-helios-accent-blue/90 shadow-sm transition-colors"
          >
            <ArrowDownToLine className="w-3.5 h-3.5" />
            <span>Export Audit Log</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Runs */}
        <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Pipeline Runs</span>
            <Activity className="w-4 h-4 text-helios-accent-blue" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {usage?.total_runs?.toLocaleString() ?? '—'}
            </span>
            <span className="text-xs text-slate-400">total lifetime</span>
          </div>
        </div>

        {/* Rows Ingested */}
        <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Rows Ingested</span>
            <Database className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              {usage?.total_rows_ingested?.toLocaleString() ?? '—'}
            </span>
            <span className="text-xs text-slate-400">bronze rows</span>
          </div>
        </div>

        {/* Total Batches */}
        <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Batches</span>
            <Layers className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-purple-600 dark:text-purple-400">
              {usage?.total_batches?.toLocaleString() ?? '—'}
            </span>
            <span className="text-xs text-slate-400">processed</span>
          </div>
        </div>

        {/* Active Tenants */}
        <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Active Tenants</span>
            <Users className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-amber-600 dark:text-amber-400">
              {usage?.active_tenants_count?.toLocaleString() ?? '—'}
            </span>
            <span className="text-xs text-slate-400">with activity</span>
          </div>
        </div>
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Pipeline Runs Over Time (Area Chart with Success vs Fail) */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Activity className="w-4 h-4 text-helios-accent-blue" />
                <span>Daily Pipeline Runs Over Time</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Execution volume by day (successful vs failed)</p>
            </div>
          </div>
          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mr-2 text-helios-accent-blue" />
                Loading pipeline history...
              </div>
            ) : (usage?.pipeline_runs_per_day || []).length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No pipeline runs recorded in telemetry yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={usage?.pipeline_runs_per_day}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke={textColor}
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => val.slice(5)} // MM-DD
                  />
                  <YAxis stroke={textColor} fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      borderColor: tooltipBorder,
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Area
                    type="monotone"
                    dataKey="successful_runs"
                    name="Successful Runs"
                    stroke="#10B981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorSuccess)"
                  />
                  <Area
                    type="monotone"
                    dataKey="failed_runs"
                    name="Failed Runs"
                    stroke="#EF4444"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorFailed)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* 2. Rows Ingested Over Time (Area Chart) */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-500" />
                <span>Bronze Ingestion Volume Over Time</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Total rows staged and processed per day</p>
            </div>
          </div>
          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mr-2 text-helios-accent-blue" />
                Loading ingestion history...
              </div>
            ) : (usage?.total_rows_ingested_over_time || []).length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No row ingestion history recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={usage?.total_rows_ingested_over_time}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorRows" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke={textColor}
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => val.slice(5)} // MM-DD
                  />
                  <YAxis
                    stroke={textColor}
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => (val >= 1000 ? `${(val / 1000).toFixed(0)}k` : `${val}`)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      borderColor: tooltipBorder,
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                    }}
                    formatter={(val: number) => [`${val.toLocaleString()} rows`, 'Rows Ingested']}
                  />
                  <Area
                    type="monotone"
                    dataKey="rows_ingested"
                    name="Rows Ingested"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRows)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* 3. Batches Processed per Tenant (Bar Chart) */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              <span>Ingestion Batches Distribution by Tenant</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Completed batch uploads and sync executions per organization</p>
          </div>
        </div>
        <div className="h-64 w-full">
          {isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              <RefreshCw className="w-5 h-5 animate-spin mr-2 text-helios-accent-blue" />
              Loading tenant batch distribution...
            </div>
          ) : (usage?.batches_per_tenant || []).length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No batches recorded for any tenant.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={usage?.batches_per_tenant}
                margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis
                  dataKey="tenant_name"
                  stroke={textColor}
                  fontSize={11}
                  tickLine={false}
                  interval={0}
                />
                <YAxis stroke={textColor} fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: tooltipBg,
                    borderColor: tooltipBorder,
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                  }}
                  formatter={(val: number) => [`${val} batches`, 'Total Batches']}
                />
                <Bar dataKey="batch_count" name="Batches" fill="#8B5CF6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Export Audit Log Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-helios-accent-blue" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Export System ETL Audit Log
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowExportModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Download the unified system ETL audit log as CSV containing batch executions, row counts, stage status, duration, and error traces.
            </p>

            {exportError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 text-xs">
                {exportError}
              </div>
            )}

            <form onSubmit={handleExportAudit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-400 mb-1">
                  Start Date (Optional)
                </label>
                <input
                  type="date"
                  value={exportStartDate}
                  onChange={(e) => setExportStartDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-400 mb-1">
                  End Date (Optional)
                </label>
                <input
                  type="date"
                  value={exportEndDate}
                  onChange={(e) => setExportEndDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowExportModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-black/5 dark:bg-white/5 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isExporting}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-helios-accent-blue text-white disabled:opacity-50"
                >
                  {isExporting ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Download className="w-3.5 h-3.5" />
                  )}
                  <span>{isExporting ? 'Generating CSV...' : 'Download CSV'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsageDashboard;
