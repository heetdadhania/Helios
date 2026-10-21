import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Building2,
  Users,
  UserCheck,
  Clock,
  Activity,
  AlertCircle,
  MessageSquare,
  Plus,
  ArrowRight,
  RefreshCw,
  TrendingUp,
  BarChart3,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { adminHomeService } from '@/services/adminHomeService';
import { AdminHomeResponse } from '@/types/adminHome';
import { formatINR, formatCountIN, formatDateIN, formatDateTimeIN } from '@/utils/currency';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { StageStatusBadge } from '@/components/admin/StageStatusBadge';
import { useTheme } from '@/hooks/useTheme';

export const AdminHome: React.FC = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [data, setData] = useState<AdminHomeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (background: boolean = false) => {
    if (background) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);
    try {
      const res = await adminHomeService.getAdminHome();
      setData(res);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to load operational oversight data. Please try again.'
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const gridColor = isDark ? '#334155' : '#E2E8F0';
  const textColor = isDark ? '#94A3B8' : '#64748B';
  const tooltipBg = isDark ? '#1E293B' : '#FFFFFF';
  const tooltipBorder = isDark ? '#334155' : '#E2E8F0';

  // Error State with Retry
  if (error && !data) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="p-8 rounded-card bg-rose-500/10 border border-rose-500/30 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-rose-700 dark:text-rose-300">
              Unable to load Admin Home
            </h3>
            <p className="text-xs text-rose-600/80 dark:text-rose-400/80 mt-1 max-w-md mx-auto">
              {error}
            </p>
          </div>
          <button
            onClick={() => loadData(false)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-control bg-helios-accent-blue text-white text-xs font-semibold hover:bg-blue-600 transition shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Top Header & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Admin Home
          </h1>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Platform operations, cross-organization ingestion health, and activity telemetry
          </p>
        </div>

        {/* Quick Actions Bar */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => navigate('/admin/tenants', { state: { openCreate: true } })}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-control bg-helios-accent-blue hover:bg-blue-600 text-white text-xs font-semibold transition shadow-sm"
            title="Register a new organization"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Organization</span>
          </button>
          <button
            onClick={() => navigate('/admin/team', { state: { openCreate: true } })}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-control bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-helios-text-primary-light dark:text-helios-text-primary-dark text-xs font-semibold transition border border-helios-border-light dark:border-helios-border-dark"
            title="Add a new platform team member"
          >
            <Users className="w-3.5 h-3.5" />
            <span>Add Team Member</span>
          </button>
          <button
            onClick={() => navigate('/admin/uploads')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-control bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-helios-text-primary-light dark:text-helios-text-primary-dark text-xs font-semibold transition border border-helios-border-light dark:border-helios-border-dark"
            title="Review pending file uploads"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Review Pending Uploads</span>
          </button>
          <button
            onClick={() => navigate('/admin/pipeline-health')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-control bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-helios-text-primary-light dark:text-helios-text-primary-dark text-xs font-semibold transition border border-helios-border-light dark:border-helios-border-dark"
            title="View pipeline health"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>View Pipeline Health</span>
          </button>
          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing || isLoading}
            className="p-2 rounded-control bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 text-helios-text-secondary-light dark:text-helios-text-secondary-dark transition border border-helios-border-light dark:border-helios-border-dark disabled:opacity-50"
            title="Refresh dashboard metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {isLoading ? (
            Array.from({ length: 7 }).map((_, idx) => (
              <LoadingSkeleton key={idx} variant="card" height={110} />
            ))
          ) : (
            <>
              {/* Card 1: Organizations */}
              <div
                onClick={() => navigate('/admin/tenants')}
                className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm hover:border-helios-accent-blue/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Organizations
                  </span>
                  <Building2 className="w-4 h-4 text-helios-accent-blue" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.organizations_total || 0)}
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                    {formatCountIN(data?.summary.organizations_active || 0)} active
                  </span>
                  {(data?.summary.organizations_inactive || 0) > 0 && (
                    <span>· {formatCountIN(data?.summary.organizations_inactive || 0)} inactive</span>
                  )}
                </div>
              </div>

              {/* Card 2: Organization Owners */}
              <div
                onClick={() => navigate('/admin/tenants')}
                className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm hover:border-helios-accent-blue/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Org Owners
                  </span>
                  <UserCheck className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.organization_owners_active || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  Active owners
                </div>
              </div>

              {/* Card 3: Team Members */}
              <div
                onClick={() => navigate('/admin/team')}
                className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm hover:border-helios-accent-blue/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Team Members
                  </span>
                  <Users className="w-4 h-4 text-sky-500" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.team_members || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  Assigned staff
                </div>
              </div>

              {/* Card 4: Pending Uploads */}
              <div
                onClick={() => navigate('/admin/uploads')}
                className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border shadow-sm cursor-pointer transition ${
                  (data?.summary.pending_uploads || 0) > 0
                    ? 'border-amber-500/50 hover:border-amber-500'
                    : 'border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue/50'
                }`}
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Pending Uploads
                  </span>
                  <Clock
                    className={`w-4 h-4 ${
                      (data?.summary.pending_uploads || 0) > 0
                        ? 'text-amber-500'
                        : 'text-slate-400'
                    }`}
                  />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.pending_uploads || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {(data?.summary.pending_uploads || 0) > 0
                    ? 'Awaiting review'
                    : 'All clear'}
                </div>
              </div>

              {/* Card 5: Running Pipelines */}
              <div
                onClick={() => navigate('/admin/pipeline-health')}
                className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm hover:border-helios-accent-blue/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Running
                  </span>
                  <Activity className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.running_pipelines || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {(data?.summary.running_pipelines || 0) > 0
                    ? 'Active executions'
                    : 'Idle'}
                </div>
              </div>

              {/* Card 6: Failed Pipelines */}
              <div
                onClick={() => navigate('/admin/pipeline-health')}
                className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border shadow-sm cursor-pointer transition ${
                  (data?.summary.failed_pipelines || 0) > 0
                    ? 'border-rose-500/50 hover:border-rose-500'
                    : 'border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue/50'
                }`}
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Failed
                  </span>
                  <AlertCircle
                    className={`w-4 h-4 ${
                      (data?.summary.failed_pipelines || 0) > 0
                        ? 'text-rose-500 animate-pulse'
                        : 'text-slate-400'
                    }`}
                  />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.failed_pipelines || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {(data?.summary.failed_pipelines || 0) > 0
                    ? 'Requires attention'
                    : 'No failures'}
                </div>
              </div>

              {/* Card 7: Open Support Messages */}
              <div
                onClick={() => navigate('/admin/support')}
                className={`p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border shadow-sm cursor-pointer transition ${
                  (data?.summary.open_support_messages || 0) > 0
                    ? 'border-amber-500/50 hover:border-amber-500'
                    : 'border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue/50'
                }`}
              >
                <div className="flex items-center justify-between text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    Support
                  </span>
                  <MessageSquare
                    className={`w-4 h-4 ${
                      (data?.summary.open_support_messages || 0) > 0
                        ? 'text-amber-500'
                        : 'text-slate-400'
                    }`}
                  />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatCountIN(data?.summary.open_support_messages || 0)}
                </div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {(data?.summary.open_support_messages || 0) > 0
                    ? 'Open inquiries'
                    : 'All answered'}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Two Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Revenue by Organization (Top 10) */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <span>Revenue by Organization (Top 10)</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Last 30 days of each organization's data
            </p>
          </div>

          <div className="h-72 w-full flex-1">
            {isLoading ? (
              <LoadingSkeleton variant="chart" height={280} />
            ) : (data?.charts.revenue_by_organization || []).length === 0 ? (
              <div className="h-full w-full flex flex-col items-center justify-center p-6 text-center rounded-xl bg-slate-50/50 dark:bg-slate-800/30 border border-dashed border-slate-200 dark:border-slate-700/60">
                <BarChart3 className="w-8 h-8 text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                  No revenue data available
                </p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                  Top organization revenues will appear once Gold order summaries are generated.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data?.charts.revenue_by_organization}
                  margin={{ top: 10, right: 10, left: 15, bottom: 35 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                  <XAxis
                    dataKey="organization_name"
                    stroke={textColor}
                    fontSize={11}
                    tickLine={false}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={40}
                  />
                  <YAxis
                    stroke={textColor}
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(val) => {
                      if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
                      if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
                      if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
                      return `₹${val}`;
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      borderColor: tooltipBorder,
                      color: isDark ? '#F5F5F5' : '#111827',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    formatter={(value: any) => [formatINR(value), 'Gross Revenue']}
                    labelFormatter={(label) => `Organization: ${label}`}
                  />
                  <Bar
                    dataKey="total_revenue"
                    fill="#10B981"
                    radius={[4, 4, 0, 0]}
                    name="Revenue"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 2: Pipeline Runs per Day (Last 14 Days) */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <Activity className="w-4 h-4 text-helios-accent-blue" />
              <span>Pipeline Runs per Day</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Split into success and failed for the last 14 days
            </p>
          </div>

          <div className="h-72 w-full flex-1">
            {isLoading ? (
              <LoadingSkeleton variant="chart" height={280} />
            ) : (data?.charts.pipeline_runs_per_day || []).length === 0 ? (
              <div className="h-full w-full flex flex-col items-center justify-center p-6 text-center rounded-xl bg-slate-50/50 dark:bg-slate-800/30 border border-dashed border-slate-200 dark:border-slate-700/60">
                <Activity className="w-8 h-8 text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                  No pipeline activity recorded
                </p>
                <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                  Execution volume will populate as pipeline batches are processed.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data?.charts.pipeline_runs_per_day}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
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
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      borderColor: tooltipBorder,
                      color: isDark ? '#F5F5F5' : '#111827',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    formatter={(value: any, name: any) => [
                      formatCountIN(value),
                      name === 'successful_runs' ? 'Success' : 'Failed',
                    ]}
                    labelFormatter={(label) => `Date: ${label}`}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    wrapperStyle={{ fontSize: '11px', paddingBottom: '8px' }}
                    formatter={(value) =>
                      value === 'successful_runs' ? 'Success' : 'Failed'
                    }
                  />
                  <Bar
                    dataKey="successful_runs"
                    stackId="runs"
                    fill="#10B981"
                    radius={[0, 0, 0, 0]}
                    name="successful_runs"
                  />
                  <Bar
                    dataKey="failed_runs"
                    stackId="runs"
                    fill="#F43F5E"
                    radius={[4, 4, 0, 0]}
                    name="failed_runs"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Two Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Table 1: Organizations */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Building2 className="w-4 h-4 text-helios-accent-blue" />
                <span>Organizations</span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Overview of tenant businesses and assignments
              </p>
            </div>
            <Link
              to="/admin/tenants"
              className="text-xs font-semibold text-helios-accent-blue hover:underline flex items-center gap-1"
            >
              <span>View all</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, idx) => (
                  <LoadingSkeleton key={idx} variant="table-row" height={36} />
                ))}
              </div>
            ) : (data?.tables.organizations || []).length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 dark:text-slate-500">
                <Building2 className="w-6 h-6 mx-auto mb-1.5 opacity-40" />
                No organizations registered yet.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    <th className="pb-2.5">Organization</th>
                    <th className="pb-2.5">Owner</th>
                    <th className="pb-2.5">Assigned Team Member</th>
                    <th className="pb-2.5 text-right">Last Data Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                  {data?.tables.organizations.map((org) => (
                    <tr
                      key={org.tenant_id}
                      onClick={() => navigate(`/admin/oversight/dashboard/${org.tenant_id}`)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-2.5 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-1.5">
                        <span className="truncate max-w-[160px]">{org.name}</span>
                        {!org.is_active && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-slate-600 dark:text-slate-300">
                        {org.owner}
                      </td>
                      <td className="py-2.5 text-slate-600 dark:text-slate-300">
                        {org.assigned_team_member}
                      </td>
                      <td className="py-2.5 text-right text-slate-500 dark:text-slate-400">
                        {org.last_data_received
                          ? formatDateIN(org.last_data_received)
                          : 'No data'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Table 2: Recent Activity */}
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" />
                <span>Recent Activity</span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Latest batch transitions across all pipelines
              </p>
            </div>
            <Link
              to="/admin/pipeline-health"
              className="text-xs font-semibold text-helios-accent-blue hover:underline flex items-center gap-1"
            >
              <span>View telemetry</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, idx) => (
                  <LoadingSkeleton key={idx} variant="table-row" height={36} />
                ))}
              </div>
            ) : (data?.tables.recent_activity || []).length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 dark:text-slate-500">
                <Activity className="w-6 h-6 mx-auto mb-1.5 opacity-40" />
                No pipeline activity recorded yet.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    <th className="pb-2.5">Batch / Organization</th>
                    <th className="pb-2.5">Stage</th>
                    <th className="pb-2.5">Status</th>
                    <th className="pb-2.5 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                  {data?.tables.recent_activity.map((act, idx) => (
                    <tr
                      key={act.batch_id || idx}
                      onClick={() => navigate('/admin/pipeline-health')}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-2.5">
                        <div className="font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {act.tenant_name || `Organization #${act.tenant_id || ''}`}
                        </div>
                        {act.batch_id && (
                          <div className="text-[10px] text-slate-400 font-mono">
                            {act.batch_id.slice(0, 8)}...
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 capitalize text-slate-600 dark:text-slate-300">
                        {act.stage ? act.stage.replace(/_/g, ' ') : '—'}
                      </td>
                      <td className="py-2.5">
                        <StageStatusBadge stage={act.stage} status={act.status} />
                      </td>
                      <td className="py-2.5 text-right text-slate-500 dark:text-slate-400">
                        {act.timestamp ? formatDateTimeIN(act.timestamp) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
