import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownToLine,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileSpreadsheet,
  Filter,
  Layers,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  X,
  XCircle,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { StageStatusBadge } from '@/components/admin/StageStatusBadge';
import { PipelineSection, SourceTypeIcon } from '@/components/admin/PipelineSection';
import { FlagForAdminButton } from '@/components/team/FlagForAdminButton';
import { pipelineHealthService } from '@/services/pipelineHealthService';
import { oversightService } from '@/services/oversightService';
import {
  PipelineRun,
  PipelineRunDetail,
} from '@/types/pipelineHealth';

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
  const [actionLoading, setActionLoading] = useState<'retry' | 'restart' | null>(null);

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
      const data = await pipelineHealthService.listRuns();
      setRuns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load pipeline executions.');
    } finally {
      setIsLoading(false);
    }
  };

  const silentPollRuns = async () => {
    try {
      const data = await pipelineHealthService.listRuns();
      setRuns(data);
    } catch {
      // Ignore background poll errors silently
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchRuns();
      const interval = setInterval(() => {
        if (document.visibilityState === 'visible') {
          silentPollRuns();
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [isAuthorized]);

  // Load Run detail when selected
  useEffect(() => {
    if (!selectedBatchId) {
      setDetail(null);
      setActionError(null);
      setActionSuccess(null);
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
    setActionLoading('retry');
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await pipelineHealthService.retryFailedStage(detail.batch_id);
      setActionSuccess(
        res.message || 'Databricks Jobs repair-run initiated. Upstream stage data preserved and reused.'
      );
      // Refresh current detail and list
      const updatedDetail = await pipelineHealthService.getRunDetail(detail.batch_id);
      setDetail(updatedDetail);
      fetchRuns();
    } catch (err: any) {
      setActionError(err.message || 'Could not retry failed stage.');
    } finally {
      setActionLoading(null);
    }
  };

  // Action: Full Restart
  const handleConfirmFullRestart = async () => {
    if (!detail) return;
    setActionLoading('restart');
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await pipelineHealthService.fullRestart(detail.batch_id);
      setActionSuccess(
        res.message || "Batch marked as 'restart_required'. A notification has been sent to the SMB Owner."
      );
      setShowRestartConfirm(false);
      // Refresh current detail and list
      const updatedDetail = await pipelineHealthService.getRunDetail(detail.batch_id);
      setDetail(updatedDetail);
      fetchRuns();
    } catch (err: any) {
      setActionError(err.message || 'Could not trigger full restart.');
    } finally {
      setActionLoading(null);
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
    const running = runs.filter((r) => {
      const norm = r.status.toLowerCase();
      return norm.includes('running') || norm === 'processing' || norm === 'in_progress' || norm === 'ingesting';
    }).length;
    const success = runs.filter((r) => {
      const norm = r.status.toLowerCase();
      return norm === 'success' || norm === 'completed';
    }).length;
    const cancelled = runs.filter((r) => r.status.toLowerCase() === 'cancelled').length;
    const rejected = runs.filter((r) => r.status.toLowerCase() === 'rejected').length;
    const stalled = runs.filter((r) => r.status.toLowerCase() === 'stalled').length;
    const restartRequired = runs.filter((r) => r.status.toLowerCase() === 'restart_required').length;
    return { total, failed, running, success, cancelled, rejected, stalled, restartRequired };
  }, [runs]);

  // Helper filter function for search query
  const matchesSearch = (r: PipelineRun): boolean => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const tenant = (r.tenant || r.tenant_name || '').toLowerCase();
    const batchId = (r.batch_id || '').toLowerCase();
    const source = (r.source_type || '').toLowerCase();
    const stage = (r.current_stage || '').toLowerCase();
    return tenant.includes(q) || batchId.includes(q) || source.includes(q) || stage.includes(q);
  };

  // Partition runs by section/status with search filtering
  const runningRuns = useMemo(() => {
    return runs.filter((r) => {
      const norm = r.status.toLowerCase();
      const isRunning = norm.includes('running') || norm === 'processing' || norm === 'in_progress' || norm === 'ingesting';
      return isRunning && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const failedRuns = useMemo(() => {
    return runs.filter((r) => {
      return r.status.toLowerCase() === 'failed' && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const successRuns = useMemo(() => {
    return runs.filter((r) => {
      const norm = r.status.toLowerCase();
      return (norm === 'success' || norm === 'completed') && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const stalledRuns = useMemo(() => {
    return runs.filter((r) => {
      return r.status.toLowerCase() === 'stalled' && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const cancelledRuns = useMemo(() => {
    return runs.filter((r) => {
      return r.status.toLowerCase() === 'cancelled' && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const rejectedRuns = useMemo(() => {
    return runs.filter((r) => {
      return r.status.toLowerCase() === 'rejected' && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const restartRequiredRuns = useMemo(() => {
    return runs.filter((r) => {
      return r.status.toLowerCase() === 'restart_required' && matchesSearch(r);
    });
  }, [runs, searchQuery]);

  const handleCancelRun = useCallback(async (batchId: string) => {
    try {
      await pipelineHealthService.cancelRun(batchId);
      await fetchRuns();
      if (selectedBatchId === batchId) {
        const updated = await pipelineHealthService.getRunDetail(batchId);
        setDetail(updated);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel pipeline run.');
    }
  }, [selectedBatchId]);


  const handleInspect = useCallback((batchId: string) => {
    setSelectedBatchId(batchId);
  }, []);

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

      {/* Global Error Notice if initial fetch failed */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="font-semibold">{error}</span>
          </div>
          <button
            onClick={fetchRuns}
            className="px-3 py-1 bg-rose-500 text-white rounded-lg font-semibold hover:bg-rose-600 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setSelectedStatus('all')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'all'
              ? 'border-helios-accent-blue bg-helios-accent-blue/5 shadow-sm'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-slate-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            <span>Total Executions</span>
            <Layers className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold mt-1 text-helios-text-primary-light dark:text-helios-text-primary-dark">
            {isLoading ? '...' : metrics.total}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('failed')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'failed'
              ? 'border-rose-500 bg-rose-500/10 shadow-sm'
              : 'border-rose-500/30 bg-helios-card-light dark:bg-helios-card-dark hover:border-rose-500'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-rose-600 dark:text-rose-400 font-semibold">
            <span>Failed Runs</span>
            <AlertCircle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold mt-1 text-rose-600 dark:text-rose-400">
            {isLoading ? '...' : metrics.failed}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('running')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'running'
              ? 'border-blue-500 bg-blue-500/10 shadow-sm'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-blue-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 font-semibold">
            <span>In-Progress</span>
            <Loader2 className={`w-4 h-4 text-blue-500 ${metrics.running > 0 ? 'animate-spin' : ''}`} />
          </div>
          <div className="text-2xl font-bold mt-1 text-blue-600 dark:text-blue-400">
            {isLoading ? '...' : metrics.running}
          </div>
        </div>

        <div
          onClick={() => setSelectedStatus('success')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            selectedStatus === 'success'
              ? 'border-emerald-500 bg-emerald-500/10 shadow-sm'
              : 'border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:border-emerald-400'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
            <span>Succeeded</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">
            {isLoading ? '...' : metrics.success}
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchRuns}
            className="px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 font-bold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Filter className="w-4 h-4 text-slate-400 ml-1 mr-1 flex-shrink-0" />
          {[
            { id: 'all', label: 'All Sections' },
            { id: 'running', label: 'Running', count: metrics.running },
            { id: 'failed', label: 'Failed', count: metrics.failed, alert: metrics.failed > 0 },
            { id: 'success', label: 'Success', count: metrics.success },
            { id: 'stalled', label: 'Stalled', count: metrics.stalled, alert: metrics.stalled > 0 },
            { id: 'cancelled', label: 'Cancelled', count: metrics.cancelled },
            { id: 'rejected', label: 'Rejected', count: metrics.rejected },
            { id: 'restart_required', label: 'Restart Required', count: metrics.restartRequired },
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
              {tab.count !== undefined && !isLoading && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    selectedStatus === tab.id
                      ? 'bg-white/20 text-white'
                      : 'bg-black/5 dark:bg-white/10 text-slate-400'
                  }`}
                >
                  {tab.count}
                </span>
              )}
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
            placeholder="Search organization, batch ID, or stage..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder-slate-400 focus:outline-none focus:border-helios-accent-blue"
          />
        </div>
      </div>

      {/* INDEPENDENT SECTIONS: Running, Failed, Success, Stalled, Cancelled, Rejected, Restart Required */}
      <div className="space-y-6">
        {/* 1. RUNNING & IN-PROGRESS SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'running') && (
          <PipelineSection
            id="running"
            title="Running & In-Progress Pipelines"
            subtitle="Batches currently actively executing across Databricks stages"
            icon={<Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />}
            count={runningRuns.length}
            variant="blue"
            runs={runningRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No running runs"
            emptyDescription="There are currently no active or in-progress pipeline executions. Upstream ingestion stages are idle or completed."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-500">
                <Activity className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
            onCancel={handleCancelRun}
          />
        )}

        {/* 2. FAILED PIPELINES SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'failed') && (
          <PipelineSection
            id="failed"
            title="Failed Pipelines"
            subtitle="Executions halted due to errors; require stage retry or restart"
            icon={<AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0" />}
            count={failedRuns.length}
            variant="rose"
            runs={failedRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No failed runs"
            emptyDescription="All pipeline executions are running smoothly. Zero stages currently require failure recovery or attention."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
                <CheckCircle2 className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}

        {/* 3. SUCCESSFUL PIPELINES SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'success') && (
          <PipelineSection
            id="success"
            title="Successful Pipelines"
            subtitle="Completed Medallion pipeline runs committed into Unity Catalog"
            icon={<CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />}
            count={successRuns.length}
            variant="emerald"
            runs={successRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No succeeded runs"
            emptyDescription="No successful pipeline executions found."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-slate-500/10 border border-slate-500/20 flex items-center justify-center text-slate-400">
                <Layers className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}

        {/* 4. STALLED PIPELINES SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'stalled') && (
          <PipelineSection
            id="stalled"
            title="Stalled Pipelines"
            subtitle="Batches with no worker heartbeat update within timeout threshold"
            icon={<AlertTriangle className="w-5 h-5 text-orange-500 flex-shrink-0" />}
            count={stalledRuns.length}
            variant="amber"
            runs={stalledRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No stalled runs"
            emptyDescription="No pipeline batches currently experiencing stalled heartbeat timeouts."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500">
                <AlertTriangle className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}

        {/* 5. CANCELLED PIPELINES SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'cancelled') && (
          <PipelineSection
            id="cancelled"
            title="Cancelled Pipelines"
            subtitle="Batches where execution was cleanly halted via cancellation"
            icon={<XCircle className="w-5 h-5 text-zinc-500 flex-shrink-0" />}
            count={cancelledRuns.length}
            variant="slate"
            runs={cancelledRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No cancelled runs"
            emptyDescription="No pipeline batches have been cancelled."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-zinc-500/10 border border-zinc-500/20 flex items-center justify-center text-zinc-500">
                <XCircle className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}

        {/* 6. REJECTED PIPELINES SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'rejected') && (
          <PipelineSection
            id="rejected"
            title="Rejected Pipelines"
            subtitle="Batches rejected during review; Bronze rows preserved for compliance"
            icon={<XCircle className="w-5 h-5 text-rose-500 flex-shrink-0" />}
            count={rejectedRuns.length}
            variant="rose"
            runs={rejectedRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No rejected runs"
            emptyDescription="No pending uploads or batches have been rejected."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500">
                <XCircle className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}

        {/* 7. RESTART REQUIRED SECTION */}
        {(selectedStatus === 'all' || selectedStatus === 'restart_required') && (
          <PipelineSection
            id="restart_required"
            title="Restart Required Pipelines"
            subtitle="Batches marked for Organization Owner re-upload or external database re-sync"
            icon={<RotateCcw className="w-5 h-5 text-amber-500 flex-shrink-0" />}
            count={restartRequiredRuns.length}
            variant="amber"
            runs={restartRequiredRuns}
            isLoading={isLoading}
            searchQuery={searchQuery}
            emptyTitle="No runs requiring restart"
            emptyDescription="No pipeline batches currently require organization file re-upload or connection reset."
            emptyIcon={
              <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
                <RotateCcw className="w-6 h-6" />
              </div>
            }
            onInspect={handleInspect}
          />
        )}
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
                    <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-start justify-between gap-2 animate-fadeIn">
                      <div className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <span className="font-medium">{actionSuccess}</span>
                      </div>
                      <button
                        onClick={() => setActionSuccess(null)}
                        className="text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-200 p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {actionError && !showRestartConfirm && (
                    <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 flex items-start justify-between gap-2 animate-fadeIn">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                        <span className="font-medium">{actionError}</span>
                      </div>
                      <button
                        onClick={() => setActionError(null)}
                        className="text-rose-500 hover:text-rose-700 dark:hover:text-rose-200 p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Error Callout if Failed */}
                  {(detail?.error_message || detail?.failure_message || detail?.failed_stage) && (
                    <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
                      <div className="flex items-center gap-2 font-semibold text-rose-600 dark:text-rose-400 text-xs">
                        <AlertCircle className="w-4 h-4 text-rose-500" />
                        <span>Execution Stopped Due To Error:</span>
                      </div>
                      {detail?.failed_stage && (
                        <div className="text-xs">
                          <span className="font-semibold text-rose-600 dark:text-rose-400">Failed Stage: </span>
                          <span className="font-mono text-slate-700 dark:text-slate-200">{detail.failed_stage}</span>
                        </div>
                      )}
                      {(detail?.failure_message || detail?.error_message) && (
                        <pre className="p-3 rounded-lg bg-black/40 text-rose-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap leading-relaxed">
                          {detail?.failure_message || detail?.error_message}
                        </pre>
                      )}
                      {detail?.failure_next_step && (
                        <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-xs">
                          <span className="font-semibold">Recommended Next Step: </span>
                          <span>{detail.failure_next_step}</span>
                        </div>
                      )}
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

            {/* Modal Footer with Actions */}
            <div className="p-4 border-t border-helios-border-light dark:border-helios-border-dark flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-black/[0.02] dark:bg-white/[0.02]">
              <div className="text-[11px] text-slate-400">
                {detail?.status.toLowerCase() === 'failed' ? (
                  <span>Select recovery action to repair pipeline execution.</span>
                ) : (
                  <span>
                    Execution state:{' '}
                    <strong className="text-helios-text-primary-light dark:text-helios-text-primary-dark capitalize">
                      {detail?.status.replace(/_/g, ' ')}
                    </strong>
                  </span>
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

                {detail?.status && (detail.status.toLowerCase().includes('running') || detail.status.toLowerCase() === 'processing' || detail.status.toLowerCase() === 'in_progress' || detail.status.toLowerCase() === 'ingesting') && (
                  <button
                    type="button"
                    disabled={actionLoading !== null}
                    onClick={async () => {
                      if (!detail) return;
                      setActionLoading('cancel' as any);
                      setActionError(null);
                      try {
                        await pipelineHealthService.cancelRun(detail.batch_id);
                        setActionSuccess('Pipeline run cancelled successfully.');
                        const updated = await pipelineHealthService.getRunDetail(detail.batch_id);
                        setDetail(updated);
                        fetchRuns();
                      } catch (err: any) {
                        setActionError(err?.message || 'Failed to cancel pipeline run.');
                      } finally {
                        setActionLoading(null);
                      }
                    }}
                    className="px-3.5 py-2 rounded-lg border border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Cancel Run</span>
                  </button>
                )}

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
                      disabled={actionLoading !== null}
                      onClick={() => {
                        setActionError(null);
                        setShowRestartConfirm(true);
                      }}
                      className="px-3.5 py-2 rounded-lg border border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50"
                      title="Mark batch restart_required and notify Organization Owner"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Full Restart</span>
                    </button>

                    {/* Primary Action: Retry from Failed Stage */}
                    <button
                      type="button"
                      disabled={actionLoading !== null}
                      onClick={handleRetryFailedStage}
                      className="px-4 py-2 rounded-lg bg-helios-accent-blue text-white hover:bg-blue-600 text-xs font-bold transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
                      title="Re-run only the failed stage via Databricks Jobs repair API, reusing clean upstream data"
                    >
                      {actionLoading === 'retry' ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Retrying Stage...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>Retry from Failed Stage</span>
                        </>
                      )}
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
              <p className="font-semibold">Organization Owner Action Required:</p>
              <p className="text-[11px]">
                An alert notification will be automatically delivered to the Organization Owner for <strong>{detail.tenant || 'this organization'}</strong>, asking them to resubmit their original source file or re-trigger their database sync.
              </p>
            </div>

            {/* Error banner inside confirmation dialog if restart fails */}
            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2 animate-fadeIn">
                <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                <span className="flex-1 font-medium">{actionError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  if (actionLoading !== 'restart') {
                    setShowRestartConfirm(false);
                    setActionError(null);
                  }
                }}
                disabled={actionLoading !== null}
                className="px-3.5 py-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={actionLoading !== null}
                onClick={handleConfirmFullRestart}
                className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all shadow flex items-center gap-1.5 disabled:opacity-50"
              >
                {actionLoading === 'restart' ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Initiating Restart...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Send Alert & Require Re-Upload</span>
                  </>
                )}
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
