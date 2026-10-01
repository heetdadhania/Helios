import React, { useEffect, useState, useMemo } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Database,
  Filter,
  Layers,
  Loader2,
  Play,
  Radio,
  RefreshCw,
  RotateCcw,
  Search,
  UploadCloud,
  X,
  ArrowDownToLine,
  Download,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { StageStatusBadge } from '@/components/admin/StageStatusBadge';
import { FlagForAdminButton } from '@/components/team/FlagForAdminButton';
import { pipelineHealthService } from '@/services/pipelineHealthService';
import { oversightService } from '@/services/oversightService';
import {
  PipelineRun,
  PipelineRunDetail,
  IngestionSourceType,
} from '@/types/pipelineHealth';

const SourceTypeIcon: React.FC<{ type: IngestionSourceType }> = ({ type }) => {
  const norm = (type || '').toLowerCase();
  if (norm === 'db_connection' || norm.includes('db')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
        <Database className="w-3 h-3 flex-shrink-0" />
        <span>DB Sync</span>
      </span>
    );
  }
  if (norm === 'api_push' || norm.includes('api')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
        <Radio className="w-3 h-3 flex-shrink-0" />
        <span>API Push</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
      <UploadCloud className="w-3 h-3 flex-shrink-0" />
      <span>File Upload</span>
    </span>
  );
};

export const PipelineHealth: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  // Role Gate check: Only team_member or admin
  const isAuthorized =
    isAuthenticated && user && (user.role === 'team_member' || user.role === 'admin');

  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected Detail Modal state
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PipelineRunDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  // Full Restart Confirmation Dialog state
  const [showRestartConfirm, setShowRestartConfirm] = useState<boolean>(false);
  const [copiedBatch, setCopiedBatch] = useState<boolean>(false);

  // Export Audit Log Dialog state
  const [showExportModal, setShowExportModal] = useState<boolean>(false);
  const [exportStartDate, setExportStartDate] = useState<string>('');
  const [exportEndDate, setExportEndDate] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);

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

  // Load runs
  const fetchRuns = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await pipelineHealthService.listRuns(
        selectedStatus !== 'all' ? selectedStatus : undefined
      );
      setRuns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load pipeline executions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchRuns();
    }
  }, [selectedStatus, isAuthorized]);

  // Load Run detail when selected
  useEffect(() => {
    if (!selectedBatchId) {
      setDetail(null);
      return;
    }
    let isMounted = true;
    const loadDetail = async () => {
      setIsDetailLoading(true);
      setActionError(null);
      setActionSuccess(null);
      try {
        const data = await pipelineHealthService.getRunDetail(selectedBatchId);
        if (isMounted) setDetail(data);
      } catch (err: any) {
        if (isMounted) setActionError(err.message || 'Failed to fetch batch detail.');
      } finally {
        if (isMounted) setIsDetailLoading(false);
      }
    };
    loadDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedBatchId]);

  // Action: Retry from Failed Stage
  const handleRetryFailedStage = async () => {
    if (!detail) return;
    setIsActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await pipelineHealthService.retryFailedStage(detail.batch_id);
      setActionSuccess(res.message);
      // Refresh current detail and list
      const updatedDetail = await pipelineHealthService.getRunDetail(detail.batch_id);
      setDetail(updatedDetail);
      fetchRuns();
    } catch (err: any) {
      setActionError(err.message || 'Could not retry failed stage.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Action: Full Restart
  const handleConfirmFullRestart = async () => {
    if (!detail) return;
    setIsActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await pipelineHealthService.fullRestart(detail.batch_id);
      setActionSuccess(res.message);
      setShowRestartConfirm(false);
      // Refresh current detail and list
      const updatedDetail = await pipelineHealthService.getRunDetail(detail.batch_id);
      setDetail(updatedDetail);
      fetchRuns();
    } catch (err: any) {
      setActionError(err.message || 'Could not trigger full restart.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedBatch(true);
    setTimeout(() => setCopiedBatch(false), 2000);
  };

  // Metrics summary
  const metrics = useMemo(() => {
    const total = runs.length;
    const failed = runs.filter((r) => r.status.toLowerCase() === 'failed').length;
    const running = runs.filter(
      (r) => r.status.includes('running') || r.status === 'processing'
    ).length;
    const success = runs.filter((r) => r.status.toLowerCase() === 'success').length;
    return { total, failed, running, success };
  }, [runs]);

  // Filtered runs
  const filteredRuns = useMemo(() => {
    return runs.filter((r) => {
      const matchesSearch =
        !searchQuery ||
        (r.tenant && r.tenant.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (r.batch_id && r.batch_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (r.source_type && r.source_type.toLowerCase().includes(searchQuery.toLowerCase()));

      const norm = r.status.toLowerCase();
      let matchesTab = true;
      if (selectedStatus === 'failed') matchesTab = norm === 'failed';
      else if (selectedStatus === 'running') matchesTab = norm.includes('running') || norm === 'processing';
      else if (selectedStatus === 'success') matchesTab = norm === 'success';
      else if (selectedStatus === 'restart_required') matchesTab = norm === 'restart_required';

      return matchesSearch && matchesTab;
    });
  }, [runs, searchQuery, selectedStatus]);

  // Enforce role isolation
  if (!isAuthorized) {
    return <Navigate to="/client/dashboard" replace />;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
            <Activity className="w-6 h-6 text-helios-accent-blue" />
            <span>Pipeline Health & Recovery</span>
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Real-time stage tracking across Bronze, Silver, and Gold pipelines. Repair failed tasks or initiate controlled restarts.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setShowExportModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-accent-blue text-white hover:bg-helios-accent-blue/90 shadow-sm transition-colors"
          >
            <ArrowDownToLine className="w-3.5 h-3.5" />
            <span>Export Audit Log</span>
          </button>
          <button
            onClick={fetchRuns}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-helios-accent-blue' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setSelectedStatus('all')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'all'
              ? 'border-helios-accent-blue bg-helios-accent-blue/5'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-slate-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            <span>Total Executions</span>
            <Layers className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold mt-1 text-helios-text-primary-light dark:text-helios-text-primary-dark">
            {metrics.total}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('failed')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'failed'
              ? 'border-rose-500 bg-rose-500/10'
              : 'border-rose-500/30 bg-helios-card-light dark:bg-helios-card-dark hover:border-rose-500'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-rose-600 dark:text-rose-400 font-semibold">
            <span>Failed Runs</span>
            <AlertCircle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold mt-1 text-rose-600 dark:text-rose-400">
            {metrics.failed}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('running')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'running'
              ? 'border-blue-500 bg-blue-500/10'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-blue-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 font-semibold">
            <span>In-Progress</span>
            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          </div>
          <div className="text-2xl font-bold mt-1 text-blue-600 dark:text-blue-400">
            {metrics.running}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('success')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'success'
              ? 'border-emerald-500 bg-emerald-500/10'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-emerald-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
            <span>Succeeded</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">
            {metrics.success}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Filter className="w-4 h-4 text-slate-400 ml-1 mr-1 flex-shrink-0" />
          {[
            { id: 'all', label: 'All' },
            { id: 'failed', label: 'Failed', alert: metrics.failed > 0 },
            { id: 'running', label: 'Running' },
            { id: 'success', label: 'Success' },
            { id: 'restart_required', label: 'Restart Required' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedStatus(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                selectedStatus === tab.id
                  ? 'bg-helios-accent-blue text-white shadow-sm'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              <span>{tab.label}</span>
              {tab.alert && (
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              )}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search tenant or batch ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder-slate-400 focus:outline-none focus:border-helios-accent-blue"
          />
        </div>
      </div>

      {/* Main Runs Table */}
      <div className="rounded-xl overflow-hidden bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4 font-semibold">Tenant</th>
                <th className="py-3 px-4 font-semibold">Source</th>
                <th className="py-3 px-4 font-semibold">Current / Stopped Stage</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Timestamp</th>
                <th className="py-3 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-helios-accent-blue" />
                    <span>Loading pipeline runs...</span>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-rose-500 font-medium">
                    <AlertCircle className="w-6 h-6 mx-auto mb-2 text-rose-500" />
                    <span>{error}</span>
                  </td>
                </tr>
              ) : filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Activity className="w-6 h-6 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
                    <span>No pipeline runs found matching criteria.</span>
                  </td>
                </tr>
              ) : (
                filteredRuns.map((run) => {
                  const isFailed = run.status.toLowerCase() === 'failed';
                  return (
                    <tr
                      key={run.batch_id}
                      onClick={() => setSelectedBatchId(run.batch_id)}
                      className={`hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer group ${
                        isFailed ? 'bg-rose-500/[0.02]' : ''
                      }`}
                    >
                      <td className="py-3 px-4 font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        <div className="font-semibold text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {run.tenant || run.tenant_name || `Tenant ${run.tenant_id}`}
                        </div>
                        <div className="font-mono text-[10px] text-slate-400 truncate max-w-[140px]">
                          {run.batch_id}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <SourceTypeIcon type={run.source_type} />
                      </td>

                      <td className="py-3 px-4">
                        <StageStatusBadge
                          stage={run.current_stage}
                          status={run.status}
                        />
                      </td>

                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark capitalize">
                          {run.status.replace(/_/g, ' ')}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark text-[11px]">
                        {run.started_at
                          ? new Date(run.started_at).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedBatchId(run.batch_id);
                          }}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold transition-colors ${
                            isFailed
                              ? 'bg-rose-500/10 text-rose-600 hover:bg-rose-500/20'
                              : 'bg-black/5 dark:bg-white/5 text-slate-600 dark:text-slate-300 hover:bg-black/10'
                          }`}
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* DETAIL MODAL / DRAWER */}
      {selectedBatchId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div
            className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-5 border-b border-helios-border-light dark:border-helios-border-dark flex items-start justify-between bg-black/[0.02] dark:bg-white/[0.02]">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Run Inspection: {detail?.tenant || detail?.tenant_name || 'Batch Details'}
                  </h3>
                  {detail && (
                    <StageStatusBadge
                      stage={detail.current_stage}
                      status={detail.status}
                    />
                  )}
                  {detail && detail.status.toLowerCase() === 'failed' && (
                    <FlagForAdminButton
                      tenantId={detail.tenant_id}
                      batchId={detail.batch_id}
                      tenantName={detail.tenant || detail.tenant_name}
                      variant="compact"
                      label="Flag for Admin"
                    />
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-400">
                  <span className="font-mono flex items-center gap-1">
                    ID: {selectedBatchId}
                    <button
                      onClick={() => copyToClipboard(selectedBatchId)}
                      className="hover:text-helios-accent-blue"
                      title="Copy Batch ID"
                    >
                      {copiedBatch ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </span>
                  <span>•</span>
                  {detail && <SourceTypeIcon type={detail.source_type} />}
                </div>
              </div>
              <button
                onClick={() => setSelectedBatchId(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {isDetailLoading ? (
                <div className="py-16 text-center text-slate-400">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-helios-accent-blue" />
                  <span>Loading stage history and audit trace...</span>
                </div>
              ) : (
                <>
                  {/* Action Banners */}
                  {actionSuccess && (
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span>{actionSuccess}</span>
                    </div>
                  )}

                  {actionError && (
                    <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                      <span>{actionError}</span>
                    </div>
                  )}

                  {/* Error Callout if Failed */}
                  {detail?.error_message && (
                    <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
                      <div className="flex items-center gap-2 font-semibold text-rose-600 dark:text-rose-400 text-xs">
                        <AlertCircle className="w-4 h-4 text-rose-500" />
                        <span>Execution Stopped Due To Error:</span>
                      </div>
                      <pre className="p-3 rounded-lg bg-black/40 text-rose-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {detail.error_message}
                      </pre>
                    </div>
                  )}

                  {/* Stage-by-Stage History Timeline */}
                  <div>
                    <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark uppercase tracking-wider mb-3">
                      Medallion Stage Progression
                    </h4>
                    {detail?.stage_history && detail.stage_history.length > 0 ? (
                      <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-helios-border-light dark:before:bg-helios-border-dark">
                        {detail.stage_history.map((step, idx) => {
                          const isSuccess = step.status === 'completed' || step.status === 'success';
                          const isFailed = step.status === 'failed';
                          const isRunning = step.status.includes('running') || step.status === 'in_progress';

                          return (
                            <div key={idx} className="relative">
                              {/* Step circle marker */}
                              <div
                                className={`absolute -left-6 top-0.5 w-4 h-4 rounded-full flex items-center justify-center border-2 bg-helios-card-light dark:bg-helios-card-dark ${
                                  isSuccess
                                    ? 'border-emerald-500 text-emerald-500'
                                    : isFailed
                                    ? 'border-rose-500 text-rose-500'
                                    : isRunning
                                    ? 'border-blue-500 text-blue-500'
                                    : 'border-slate-400 text-slate-400'
                                }`}
                              >
                                {isSuccess && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                                {isFailed && <X className="w-2.5 h-2.5 stroke-[3]" />}
                                {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping" />}
                              </div>

                              <div className="p-3 rounded-lg bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark capitalize">
                                    {step.stage.replace(/_/g, ' ')}
                                  </span>
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                      isSuccess
                                        ? 'bg-emerald-500/10 text-emerald-600'
                                        : isFailed
                                        ? 'bg-rose-500/10 text-rose-600'
                                        : 'bg-blue-500/10 text-blue-600'
                                    }`}
                                  >
                                    {step.status}
                                  </span>
                                </div>

                                <div className="flex items-center gap-4 text-slate-400 text-[11px] pt-1">
                                  {step.duration_seconds !== null && step.duration_seconds !== undefined && (
                                    <span className="flex items-center gap-1 font-mono">
                                      <Clock className="w-3 h-3" />
                                      {step.duration_seconds}s
                                    </span>
                                  )}
                                  {step.row_count !== null && step.row_count !== undefined && (
                                    <span>
                                      Rows: <strong className="font-mono text-slate-300">{step.row_count.toLocaleString()}</strong>
                                    </span>
                                  )}
                                  {step.completed_at && (
                                    <span>
                                      Finished:{' '}
                                      {new Date(step.completed_at).toLocaleTimeString([], {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        second: '2-digit',
                                      })}
                                    </span>
                                  )}
                                </div>

                                {step.error_message && (
                                  <p className="text-rose-500 font-mono text-[10px] pt-1 mt-1 border-t border-rose-500/20">
                                    {step.error_message}
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-slate-400 italic">No stage history recorded yet.</p>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer with Actions for Failed Runs */}
            <div className="p-4 border-t border-helios-border-light dark:border-helios-border-dark flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-black/[0.02] dark:bg-white/[0.02]">
              <div className="text-[11px] text-slate-400">
                {detail?.status.toLowerCase() === 'failed' ? (
                  <span>Select recovery action to repair pipeline execution.</span>
                ) : (
                  <span>Execution state: <strong>{detail?.status}</strong></span>
                )}
              </div>

              <div className="flex items-center gap-3 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={() => setSelectedBatchId(null)}
                  className="px-3.5 py-2 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark text-xs font-semibold hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                >
                  Close
                </button>

                {detail?.status.toLowerCase() === 'failed' && (
                  <>
                    {/* Escalation Action: Flag for Admin */}
                    <FlagForAdminButton
                      tenantId={detail.tenant_id}
                      batchId={detail.batch_id}
                      tenantName={detail.tenant || detail.tenant_name}
                      variant="warning"
                      label="Flag for Admin"
                    />

                    {/* Secondary Action: Full Restart */}
                    <button
                      type="button"
                      disabled={isActionLoading}
                      onClick={() => setShowRestartConfirm(true)}
                      className="px-3.5 py-2 rounded-lg border border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 text-xs font-semibold transition-colors flex items-center gap-1.5"
                      title="Mark batch restart_required and notify SMB Owner"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Full Restart</span>
                    </button>

                    {/* Primary Action: Retry from Failed Stage */}
                    <button
                      type="button"
                      disabled={isActionLoading}
                      onClick={handleRetryFailedStage}
                      className="px-4 py-2 rounded-lg bg-helios-accent-blue text-white hover:bg-blue-600 text-xs font-bold transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
                      title="Re-run only the failed stage via Databricks Jobs repair API, reusing clean upstream data"
                    >
                      {isActionLoading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5 fill-current" />
                      )}
                      <span>Retry from Failed Stage</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FULL RESTART CONFIRMATION DIALOG */}
      {showRestartConfirm && detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-amber-500/40 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-500">
              <div className="p-2.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Confirm Full Ingestion Restart
                </h3>
                <span className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold">
                  Batch: {detail.batch_id}
                </span>
              </div>
            </div>

            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark leading-relaxed">
              This action will mark the batch as <strong className="text-amber-500 font-semibold">restart_required</strong> and will <strong>NOT</strong> re-run the existing batch in place.
            </p>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700 dark:text-amber-300 space-y-1">
              <p className="font-semibold">SMB Owner Action Required:</p>
              <p className="text-[11px]">
                An alert notification will be automatically delivered to the SMB Owner for <strong>{detail.tenant || 'this tenant'}</strong>, asking them to resubmit their original source file or re-trigger their database sync.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowRestartConfirm(false)}
                disabled={isActionLoading}
                className="px-3.5 py-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={isActionLoading}
                onClick={handleConfirmFullRestart}
                className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow flex items-center gap-1.5 disabled:opacity-50"
              >
                {isActionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Send Alert & Require Re-Upload</span>
              </button>
            </div>
          </div>
        </div>
      )}

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
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Generate and download the system ETL audit log as CSV containing batch executions, row counts, stage status, duration, and error traces.
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
                  className="w-full px-3 py-2 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark [color-scheme:light] dark:[color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
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
                  className="w-full px-3 py-2 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark [color-scheme:light] dark:[color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
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
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
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

export const PipelineHealthPage = PipelineHealth;
export default PipelineHealth;
