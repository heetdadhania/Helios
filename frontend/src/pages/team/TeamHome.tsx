import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  Activity,
  AlertTriangle,
  Flame,
  Building2,
  MessageSquare,
  History,
  Calendar,
  CheckCircle2,
  ArrowRight,
  Loader2,
  RefreshCw,
  UploadCloud,
  ChevronRight,
} from 'lucide-react';
import { teamHomeService } from '@/services/teamHomeService';
import { TeamHomeResponse } from '@/types/teamHome';
import { formatDateTimeIN } from '@/utils/currency';
import { useBasePath } from '@/hooks/useBasePath';

export const TeamHome: React.FC = () => {
  const navigate = useNavigate();
  const basePath = useBasePath();
  const [loading, setLoading] = useState<boolean>(true);
  const [data, setData] = useState<TeamHomeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchTeamHome = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await teamHomeService.getTeamHome();
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load team operations overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeamHome();
  }, []);

  const renderStatusBadge = (status: string | null) => {
    const s = (status || '').toLowerCase();
    if (s === 'success' || s === 'completed' || s === 'ready') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-3 h-3" />
          Success
        </span>
      );
    }
    if (s === 'pending_review' || s === 'awaiting_confirmation') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
          <Clock className="w-3 h-3" />
          Pending Review
        </span>
      );
    }
    if (s === 'running' || s === 'ingesting' || s === 'silver_running' || s === 'gold_running') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800 animate-pulse">
          <RefreshCw className="w-3 h-3 animate-spin" />
          Running
        </span>
      );
    }
    if (s === 'stalled') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-400 border border-purple-200 dark:border-purple-800">
          <Flame className="w-3 h-3 text-purple-500" />
          Stalled
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
        <AlertTriangle className="w-3 h-3" />
        {status || 'Failed'}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-helios-accent-blue">
              Operations Center
            </span>
            <span className="text-gray-300 dark:text-gray-700">·</span>
            <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
              Assigned Organizations Workspace
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Team Home
          </h1>
          <p className="text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Real-time status, items awaiting review, and support inquiries across your assigned organizations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchTeamHome}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-helios-bg-light dark:hover:bg-helios-bg-dark transition shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={() => navigate(`${basePath}/upload`)}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-sm"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Data</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="p-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-helios-accent-blue mb-3" />
          <p className="text-sm font-medium">Loading operations overview...</p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
          <button
            type="button"
            onClick={fetchTeamHome}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Content */}
      {!loading && !error && data && (
        <>
          {/* Section 1: Four Pipeline Counts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Pending Review */}
            <div
              onClick={() => navigate(`${basePath}/uploads`)}
              className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Pending Review
                </span>
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 group-hover:scale-110 transition-transform">
                  <Clock className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <div className="text-3xl font-extrabold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {data.pipeline_counts.pending_review}
                </div>
                <span className="text-xs font-medium text-helios-accent-blue flex items-center">
                  Review <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Awaiting schema confirmation
              </p>
            </div>

            {/* Running */}
            <div
              onClick={() => navigate(`${basePath}/pipeline-health`)}
              className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Running
                </span>
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform">
                  <Activity className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <div className="text-3xl font-extrabold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {data.pipeline_counts.running}
                </div>
                <span className="text-xs font-medium text-helios-accent-blue flex items-center">
                  Monitor <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Active Medallion ETL jobs
              </p>
            </div>

            {/* Failed */}
            <div
              onClick={() => navigate(`${basePath}/pipeline-health`)}
              className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Failed
                </span>
                <div className="p-2 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 group-hover:scale-110 transition-transform">
                  <AlertTriangle className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <div className="text-3xl font-extrabold text-rose-600 dark:text-rose-400">
                  {data.pipeline_counts.failed}
                </div>
                <span className="text-xs font-medium text-rose-600 dark:text-rose-400 flex items-center">
                  Diagnose <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Jobs requiring remediation
              </p>
            </div>

            {/* Stalled */}
            <div
              onClick={() => navigate(`${basePath}/pipeline-health`)}
              className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Stalled
                </span>
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 group-hover:scale-110 transition-transform">
                  <Flame className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <div className="text-3xl font-extrabold text-purple-600 dark:text-purple-400">
                  {data.pipeline_counts.stalled}
                </div>
                <span className="text-xs font-medium text-purple-600 dark:text-purple-400 flex items-center">
                  Recover <ChevronRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Lost heartbeat &gt;15 min
              </p>
            </div>
          </div>

          {/* Section 2: Assigned Organizations Table */}
          <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-helios-accent-blue" />
                <h2 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Assigned Organizations ({data.assigned_organizations.length})
                </h2>
              </div>
              <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Enforced via platform.team_assignments
              </span>
            </div>

            {data.assigned_organizations.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl">
                <Building2 className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  No organizations assigned yet.
                </p>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                  Contact an administrator to allocate organizations to your team account.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase font-semibold tracking-wider">
                      <th className="py-3 px-4">Organization Name</th>
                      <th className="py-3 px-4">Org ID</th>
                      <th className="py-3 px-4">Last Data Date</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {data.assigned_organizations.map((org) => (
                      <tr
                        key={org.tenant_id}
                        className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                      >
                        <td className="py-3.5 px-4 font-semibold">
                          {org.business_name}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-gray-500">
                          #{org.tenant_id}
                        </td>
                        <td className="py-3.5 px-4">
                          {org.last_data_date ? (
                            <span className="inline-flex items-center gap-1.5 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                              <Calendar className="w-3.5 h-3.5 text-helios-accent-blue" />
                              {org.last_data_date}
                            </span>
                          ) : (
                            <span className="text-gray-400 italic">No data recorded</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => navigate(`${basePath}/upload`)}
                            className="inline-flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold bg-helios-accent-blue/10 text-helios-accent-blue hover:bg-helios-accent-blue hover:text-white transition"
                          >
                            <UploadCloud className="w-3.5 h-3.5" />
                            <span>Upload</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Section 3 & 4 Grid: Open Support Messages & Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Open Support Messages */}
            <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-helios-accent-blue" />
                  <h2 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Open Support Messages ({data.open_support_messages.length})
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => navigate(`${basePath}/support`)}
                  className="text-xs font-semibold text-helios-accent-blue hover:underline flex items-center gap-1"
                >
                  <span>Support Inbox</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {data.open_support_messages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
                  <p className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    No open support messages
                  </p>
                  <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                    All support inquiries from assigned organizations have been resolved.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto max-h-96 pr-1">
                  {data.open_support_messages.map((msg) => (
                    <div
                      key={msg.message_id}
                      onClick={() => navigate(`${basePath}/support`)}
                      className="p-3.5 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/[0.05] dark:hover:bg-white/[0.05] transition cursor-pointer"
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {msg.tenant_name || `Organization #${msg.tenant_id}`}
                        </span>
                        <span className="text-gray-400">
                          {msg.created_at ? formatDateTimeIN(msg.created_at) : ''}
                        </span>
                      </div>
                      <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark line-clamp-2">
                        {msg.message}
                      </p>
                      <div className="mt-2 text-[11px] text-gray-500 flex items-center justify-between">
                        <span>From: {msg.from_user_name || `User #${msg.from_user_id}`}</span>
                        <span className="text-amber-600 dark:text-amber-400 font-semibold uppercase text-[10px]">
                          Open
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Activity */}
            <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-helios-accent-blue" />
                  <h2 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Recent Activity
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => navigate(`${basePath}/history`)}
                  className="text-xs font-semibold text-helios-accent-blue hover:underline flex items-center gap-1"
                >
                  <span>All History</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {data.recent_activity.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl">
                  <Activity className="w-8 h-8 text-gray-400 mb-2" />
                  <p className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    No recent activity
                  </p>
                  <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                    No recent ingestion or pipeline runs recorded for assigned organizations.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto max-h-96 pr-1">
                  {data.recent_activity.map((act, idx) => (
                    <div
                      key={act.batch_id || idx}
                      className="p-3.5 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02]"
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {act.tenant_name || `Org #${act.tenant_id}`}
                        </span>
                        {renderStatusBadge(act.status)}
                      </div>
                      <div className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-2 mt-1">
                        <span className="font-mono text-[11px] text-gray-500">
                          {act.batch_id?.substring(0, 16)}...
                        </span>
                        <span>·</span>
                        <span className="capitalize">{act.stage || 'Pipeline'}</span>
                      </div>
                      {act.error_message && (
                        <p className="text-[11px] text-rose-600 dark:text-rose-400 mt-1 line-clamp-1 font-mono">
                          {act.error_message}
                        </p>
                      )}
                      <div className="mt-1 text-[11px] text-gray-400">
                        {act.timestamp ? formatDateTimeIN(act.timestamp) : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
