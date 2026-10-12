import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Play,
  Database,
  Table,
  UploadCloud,
  Key,
  ShieldCheck,
  Loader2,
  Info,
  FileText,
  ChevronDown,
  ChevronUp,
  XCircle,
  X,
} from 'lucide-react';
import { BatchCompleteness, DataQualityLogItem, SchemaPreview, SourceType } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { FlagForAdminButton } from '@/components/team/FlagForAdminButton';

const ORDERS_TARGET_FIELDS = [
  { value: 'order_id', label: 'order_id', required: true },
  { value: 'order_date', label: 'order_date', required: true },
  { value: 'customer_id', label: 'customer_id', required: true },
  { value: 'customer_name', label: 'customer_name', required: false },
  { value: 'segment', label: 'segment', required: false },
  { value: 'product_id', label: 'product_id', required: true },
  { value: 'product_name', label: 'product_name', required: false },
  { value: 'category', label: 'category', required: false },
  { value: 'quantity', label: 'quantity', required: true },
  { value: 'unit_price', label: 'unit_price', required: true },
  { value: 'discount', label: 'discount', required: false },
  { value: 'total', label: 'total', required: true },
  { value: 'profit', label: 'profit', required: false },
];

const SHIPPING_TARGET_FIELDS = [
  { value: 'shipment_id', label: 'shipment_id', required: true },
  { value: 'tracking_number', label: 'tracking_number', required: true },
  { value: 'order_id', label: 'order_id', required: true },
  { value: 'carrier', label: 'carrier', required: false },
  { value: 'shipping_status', label: 'shipping_status', required: false },
  { value: 'shipped_at', label: 'shipped_at', required: false },
  { value: 'delivered_at', label: 'delivered_at', required: false },
  { value: 'shipping_cost', label: 'shipping_cost', required: false },
  { value: 'destination_country', label: 'destination_country', required: false },
  { value: 'destination_postal_code', label: 'destination_postal_code', required: false },
];

export const ConfirmSchema: React.FC = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();

  const [preview, setPreview] = useState<SchemaPreview | null>(null);
  const [columnOverrides, setColumnOverrides] = useState<Record<string, string>>({});
  const [silverTable, setSilverTable] = useState<string>('silver.orders_clean');
  const [notes, setNotes] = useState<string>('');
  const [completeness, setCompleteness] = useState<BatchCompleteness | null>(null);
  const [isCompletenessLoading, setIsCompletenessLoading] = useState<boolean>(false);
  const [completenessError, setCompletenessError] = useState<string | null>(null);

  const [rejectionLogs, setRejectionLogs] = useState<DataQualityLogItem[]>([]);
  const [isRejectionsLoading, setIsRejectionsLoading] = useState<boolean>(false);
  const [rejectionsError, setRejectionsError] = useState<string | null>(null);
  const [showRejections, setShowRejections] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<{ runId: string } | null>(null);

  const [isRejectOpen, setIsRejectOpen] = useState<boolean>(false);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [rejectSuccess, setRejectSuccess] = useState<boolean>(false);

  const [confirmProceedWithMissing, setConfirmProceedWithMissing] = useState<boolean>(false);

  const isShipping = (preview?.detected_template || preview?.inferred_template || '').toLowerCase().includes('ship');
  const targetFieldOptions = isShipping ? SHIPPING_TARGET_FIELDS : ORDERS_TARGET_FIELDS;

  const mappedTargets = useMemo(() => {
    return new Set(
      Object.values(columnOverrides).filter(
        (val) => val && val !== '__ignore__' && val !== 'ignore'
      )
    );
  }, [columnOverrides]);

  const unmappedRequiredFields = useMemo(() => {
    return targetFieldOptions
      .filter((opt) => opt.required && !mappedTargets.has(opt.value))
      .map((opt) => opt.value);
  }, [targetFieldOptions, mappedTargets]);

  const loadBatchDetails = React.useCallback(async () => {
    if (!batchId) return;
    setIsLoading(true);
    setError(null);
    try {
      // Step 2: Get schema preview
      const previewData = await adminService.getPreview(batchId);
      setPreview(previewData);
      setSilverTable(previewData.suggested_silver_table || 'silver.orders_clean');

      const initialOverrides: Record<string, string> = {};
      (previewData.column_mappings || []).forEach((mapping) => {
        initialOverrides[mapping.source_column] = mapping.target_field || '__ignore__';
      });
      setColumnOverrides(initialOverrides);

      // Step 2: Load completeness data in separate call with own states
      setIsCompletenessLoading(true);
      setCompletenessError(null);
      adminService
        .getCompleteness(batchId)
        .then((comp) => setCompleteness(comp))
        .catch((err) => setCompletenessError(err.message || 'Completeness data not available.'))
        .finally(() => setIsCompletenessLoading(false));

      // Step 2: Load rejection data in separate call with own states
      setIsRejectionsLoading(true);
      setRejectionsError(null);
      adminService
        .getDataQualityLogs(undefined, batchId)
        .then((logs) => {
          const matched = (logs || []).filter(
            (log) => log.batch_id === batchId || log.batch_id.toLowerCase().includes(batchId.toLowerCase())
          );
          setRejectionLogs(matched);
        })
        .catch((err) => setRejectionsError(err.message || 'Data quality logs not available.'))
        .finally(() => setIsRejectionsLoading(false));
    } catch (err: any) {
      setError(err.message || 'Failed to load schema preview.');
    } finally {
      setIsLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    loadBatchDetails();
  }, [loadBatchDetails]);

  const handleTargetChange = (sourceCol: string, targetCol: string) => {
    setColumnOverrides((prev) => ({
      ...prev,
      [sourceCol]: targetCol,
    }));
  };

  const handleConfirm = async () => {
    if (!batchId) return;
    if (unmappedRequiredFields.length > 0 && !confirmProceedWithMissing) {
      setError(`Cannot approve: Required fields [${unmappedRequiredFields.join(', ')}] are not mapped. Map them or confirm to proceed.`);
      return;
    }
    setIsConfirming(true);
    setError(null);
    try {
      const cleanedOverrides: Record<string, string> = {};
      for (const [src, tgt] of Object.entries(columnOverrides)) {
        if (tgt && tgt !== '__ignore__') {
          cleanedOverrides[src] = tgt;
        } else {
          cleanedOverrides[src] = '__ignore__';
        }
      }

      const res = await adminService.confirmUpload(batchId, {
        column_mappings: cleanedOverrides,
        silver_table: silverTable,
        notes: notes || undefined,
        internal_notes: notes || undefined,
        confirmed_template: preview?.inferred_template || preview?.detected_template || 'template_orders',
      });
      setSuccessResult({ runId: res.silver_job_run_id });
    } catch (err: any) {
      setError(err.message || 'Failed to confirm schema mapping.');
    } finally {
      setIsConfirming(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchId) return;
    if (rejectReason.trim().length < 5) {
      setRejectError('Rejection reason must be at least 5 characters.');
      return;
    }
    setIsRejecting(true);
    setRejectError(null);
    try {
      await adminService.rejectUpload(batchId, rejectReason.trim());
      setIsRejectOpen(false);
      setRejectSuccess(true);
    } catch (err: any) {
      setRejectError(err.message || 'Failed to reject upload.');
    } finally {
      setIsRejecting(false);
    }
  };

  const renderSourceTypeBadge = (type: SourceType) => {

    switch (type) {
      case 'upload':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <UploadCloud className="w-3.5 h-3.5" />
            <span>File Upload</span>
          </span>
        );
      case 'db_connection':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <Database className="w-3.5 h-3.5" />
            <span>Database Replication</span>
          </span>
        );
      case 'api_push':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <Key className="w-3.5 h-3.5" />
            <span>API Event Stream</span>
          </span>
        );
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto p-8 animate-pulse">
        <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
        <div className="h-28 w-full bg-slate-100 dark:bg-slate-900 rounded-xl" />
        <div className="h-64 w-full bg-slate-100 dark:bg-slate-900 rounded-xl" />
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="max-w-xl mx-auto p-8 text-center space-y-4">
        <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Failed to load schema preview
        </h3>
        <p className="text-xs text-rose-600 dark:text-rose-400">
          {error || 'No preview available for this batch.'}
        </p>
        <div className="pt-2">
          <button
            type="button"
            onClick={loadBatchDetails}
            className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (successResult) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
          <CheckCircle2 className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Schema Confirmed & Silver Stage Triggered
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-md mx-auto">
            Batch <strong className="font-mono text-helios-accent-blue">{batchId}</strong> has been confirmed. The Databricks Silver cleaning job has been initiated with run ID:
          </p>
          <div className="inline-block px-3 py-1 font-mono text-xs font-bold rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark">
            {successResult.runId}
          </div>
        </div>

        <div className="flex items-center justify-center gap-3 pt-4">
          <button
            type="button"
            onClick={() => navigate('/admin/pipeline-health')}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-colors"
          >
            Track in Pipeline Health
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin/uploads')}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            Return to Pending Uploads
          </button>
        </div>
      </div>
    );
  }

  if (rejectSuccess) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
          <XCircle className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Batch Rejected
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-md mx-auto">
            Batch <strong className="font-mono text-rose-500">{batchId}</strong> has been rejected. The submitter has been notified and raw Bronze rows have been preserved for auditing.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 pt-4">
          <button
            type="button"
            onClick={() => navigate('/admin/uploads')}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-colors"
          >
            Return to Pending Uploads
          </button>
        </div>
      </div>
    );
  }

  return (

    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
        <button
          type="button"
          onClick={() => navigate('/admin/uploads')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Pending Approvals</span>
        </button>

        <div className="flex items-center gap-2.5">
          {preview && (
            <FlagForAdminButton
              tenantId={preview.tenant_id}
              batchId={preview.batch_id || batchId}
              tenantName={preview.tenant_name}
              variant="compact"
            />
          )}
          {preview && renderSourceTypeBadge(preview.source_type)}
        </div>
      </div>

      {/* Batch Overview Banner */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
            Batch ID
          </span>
          <div className="text-sm font-mono font-bold text-helios-accent-blue mt-1">
            {preview?.batch_id || batchId}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {preview?.tenant_name || `Tenant #${preview?.tenant_id}`}
          </div>
        </div>

        <div>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
            Detected Template
          </span>
          <div className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-1">
            {preview?.inferred_template || 'Generic Dataset'}
          </div>
          <div className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Valid Medallion Spec</span>
          </div>
        </div>

        <div>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
            Confidence Score
          </span>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm font-mono font-bold text-helios-accent-teal">
              {Math.round(((preview?.confidence_score ?? 0) <= 1 ? (preview?.confidence_score ?? 0) * 100 : (preview?.confidence_score ?? 0)))}%
            </span>
            {unmappedRequiredFields.length > 0 ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                <AlertTriangle className="w-3 h-3 shrink-0" />
                <span>Missing: {unmappedRequiredFields.join(', ')}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3 h-3 shrink-0" />
                <span>All required mapped</span>
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Heuristic column match
          </div>
        </div>

        <div>
          <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
            Target Silver Table
          </span>
          <div className="mt-1">
            <input
              type="text"
              value={silverTable}
              onChange={(e) => setSilverTable(e.target.value)}
              className="w-full px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
        </div>
      </div>

      {/* Unmapped required fields warning banner */}
      {unmappedRequiredFields.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />
            <span>Warning: Missing Required Canonical Fields ({unmappedRequiredFields.length})</span>
          </div>
          <p>
            The following required fields are not mapped to any incoming column:{' '}
            <strong className="font-mono">{unmappedRequiredFields.join(', ')}</strong>.
            Approve & Run is locked until every required field is mapped, or you explicitly confirm to proceed.
          </p>
          <div className="pt-1 flex items-center gap-2">
            <input
              type="checkbox"
              id="confirmProceedWithMissing"
              checked={confirmProceedWithMissing}
              onChange={(e) => setConfirmProceedWithMissing(e.target.checked)}
              className="rounded border-slate-300 text-amber-600 focus:ring-amber-500 cursor-pointer"
            />
            <label htmlFor="confirmProceedWithMissing" className="font-semibold cursor-pointer">
              Confirm I want to proceed anyway with unmapped required fields
            </label>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Column Mappings Table */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        <div className="p-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Table className="w-4 h-4 text-helios-accent-blue" />
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Inferred Column Schema & Target Mapping
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            {preview?.column_mappings.length || 0} columns detected
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                <th className="py-2.5 px-4 font-semibold">Source Column (Bronze)</th>
                <th className="py-2.5 px-4 font-semibold">Inferred Type</th>
                <th className="py-2.5 px-4 font-semibold">Similarity</th>
                <th className="py-2.5 px-4 font-semibold">Match Type</th>
                <th className="py-2.5 px-4 font-semibold">Target Silver Field</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {(preview?.column_mappings || []).map((col) => {
                const currentTarget = columnOverrides[col.source_column] || '__ignore__';
                const isUnmapped = !currentTarget || currentTarget === '__ignore__';

                return (
                  <tr
                    key={col.source_column}
                    className={`transition-colors ${
                      isUnmapped
                        ? 'bg-amber-500/10 dark:bg-amber-500/15 border-l-4 border-l-amber-500'
                        : 'hover:bg-black/5 dark:hover:bg-white/5'
                    }`}
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-slate-700 dark:text-slate-200">
                      <div className="flex items-center gap-2">
                        <span>{col.source_column}</span>
                        {isUnmapped && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-700 dark:text-amber-300">
                            Unmapped / Ignored
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-helios-accent-blue text-[11px]">
                      {col.inferred_type}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                          (col.similarity_score ?? col.confidence_score ?? 0) >= 0.8
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {Math.round(((col.similarity_score ?? col.confidence_score ?? 0) <= 1 ? (col.similarity_score ?? col.confidence_score ?? 0) * 100 : (col.similarity_score ?? col.confidence_score ?? 0)))}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {col.is_exact ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">Exact</span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">Fuzzy Match</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <select
                        value={currentTarget}
                        onChange={(e) => handleTargetChange(col.source_column, e.target.value)}
                        className={`w-60 px-2.5 py-1.5 text-xs font-mono font-medium rounded-lg border focus:outline-none focus:ring-1 focus:ring-helios-accent-blue cursor-pointer ${
                          isUnmapped
                            ? 'bg-amber-500/10 dark:bg-amber-950/40 border-amber-500/40 text-amber-800 dark:text-amber-200'
                            : 'bg-black/5 dark:bg-white/5 border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark'
                        }`}
                      >
                        <option value="__ignore__">Ignore this column</option>
                        {targetFieldOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label} {opt.required ? '(Required)' : ''}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Data Completeness Indicator & Sample Bronze Rows Preview */}
      <div className="space-y-4">
        {/* Data Completeness Indicator Banner */}
        {isCompletenessLoading ? (
          <div className="p-4 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex items-center gap-3 animate-pulse">
            <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800" />
            <div className="space-y-2 flex-1">
              <div className="h-3 w-40 bg-slate-200 dark:bg-slate-800 rounded" />
              <div className="h-4 w-64 bg-slate-200 dark:bg-slate-800 rounded" />
            </div>
          </div>
        ) : completenessError ? (
          <div className="p-3.5 rounded-xl bg-slate-500/5 border border-slate-500/10 text-slate-400 text-xs flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Info className="w-4 h-4 text-slate-400" />
              <span>Completeness metrics: {completenessError}</span>
            </span>
          </div>
        ) : completeness ? (
          <div className="p-4 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs font-mono shrink-0 ${
                  completeness.completeness_percentage >= 90
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                    : completeness.completeness_percentage >= 70
                    ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                    : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                }`}
              >
                {Math.round(completeness.completeness_percentage)}%
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Data Completeness Indicator
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      completeness.completeness_percentage >= 90
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                        : completeness.completeness_percentage >= 70
                        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                    }`}
                  >
                    {completeness.completeness_percentage}% Quality
                  </span>
                </div>
                <div className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-0.5">
                  <span>{completeness.completeness_percentage}% of rows accepted</span>
                  <span className="mx-2 text-slate-300 dark:text-slate-600">—</span>
                  <span className={completeness.rejected_rows > 0 ? 'text-rose-500 dark:text-rose-400' : 'text-slate-400'}>
                    {completeness.rejected_rows} row{completeness.rejected_rows === 1 ? '' : 's'} rejected
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-xs text-slate-400 text-right hidden sm:block">
                <div>
                  Total Ingested:{' '}
                  <span className="font-mono font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {completeness.total_rows.toLocaleString()}
                  </span>
                </div>
                <div>
                  Silver Clean:{' '}
                  <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                    {completeness.accepted_rows.toLocaleString()}
                  </span>
                </div>
              </div>

              {completeness.rejected_rows > 0 && (
                <button
                  type="button"
                  onClick={() => setShowRejections((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 transition-all cursor-pointer"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>
                    {showRejections ? 'Hide rejection reasons' : `View rejection reasons (${completeness.rejected_rows})`}
                  </span>
                  {showRejections ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          </div>
        ) : null}

        {/* Expandable Rejection Reasons Panel from Data Quality Log */}
        {showRejections && (
          <div className="rounded-2xl bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/20 p-4 space-y-3 transition-all animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-500" />
                <h4 className="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
                  Data Quality Log Rejections for Batch {batchId}
                </h4>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                {rejectionLogs.length} logged record{rejectionLogs.length === 1 ? '' : 's'}
              </span>
            </div>

            {isRejectionsLoading ? (
              <div className="p-3 text-xs text-slate-400 animate-pulse">Loading data quality rejections...</div>
            ) : rejectionsError ? (
              <p className="text-xs text-rose-500 py-2">{rejectionsError}</p>
            ) : rejectionLogs.length > 0 ? (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {rejectionLogs.map((log, idx) => (
                  <div
                    key={log.id || idx}
                    className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-rose-500/10 dark:border-rose-500/20 shadow-xs flex flex-col sm:flex-row sm:items-start justify-between gap-2"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {log.error_category && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/10 text-rose-600 dark:text-rose-400">
                            {log.error_category}
                          </span>
                        )}
                        <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
                          {log.table_name || 'silver.orders_clean'}
                        </span>
                      </div>
                      <p className="text-xs text-rose-700 dark:text-rose-300 font-mono break-all">
                        {log.rejection_reason}
                      </p>
                    </div>
                    {log.timestamp && (
                      <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 py-2">
                No data quality rejections recorded for this batch.
              </p>
            )}
          </div>
        )}

        {/* Sample Bronze Rows Preview Table */}
        {preview?.sample_rows && preview.sample_rows.length > 0 && (
          <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
            <div className="p-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Info className="w-4 h-4 text-slate-400" />
                <span>Bronze Sample Rows Preview</span>
              </h3>
              <span className="text-xs text-slate-400">First {preview.sample_rows.length} rows</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                    {Object.keys(preview.sample_rows[0]).map((key) => (
                      <th key={key} className="py-2 px-3 font-semibold text-[11px] whitespace-nowrap">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-slate-600 dark:text-slate-300">
                  {preview.sample_rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-black/5 dark:hover:bg-white/5">
                      {Object.values(row).map((val: any, colIdx) => (
                        <td key={colIdx} className="py-2 px-3 whitespace-nowrap text-[11px]">
                          {String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Action Section with Internal Notes */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-4">
        <div>
          {/* Read-only Previous Internal Note Context */}
          {preview?.internal_notes && (
            <div className="mb-3 p-3.5 rounded-xl bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/20 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-bold text-blue-600 dark:text-blue-400">
                <FileText className="w-3.5 h-3.5" />
                <span>Previous Internal Note</span>
              </div>
              <p className="text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark whitespace-pre-wrap leading-relaxed font-sans">
                {preview.internal_notes}
              </p>
            </div>
          )}

          <label className="block text-xs font-semibold text-slate-400 mb-1">
            Internal Notes
          </label>
          <textarea
            rows={3}
            placeholder="Add internal notes, reviewer observations, or instructions for other team members and admins..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 text-xs rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue resize-y"
          />
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <p className="text-xs text-slate-400">
            Confirming this schema records an immutable audit log, stores internal reviewer notes, and dispatches the Databricks Silver cleaning job.
          </p>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            {preview && (
              <FlagForAdminButton
                tenantId={preview.tenant_id}
                batchId={preview.batch_id || batchId}
                tenantName={preview.tenant_name}
                variant="button"
                label="Flag for Admin"
              />
            )}

            <button
              type="button"
              onClick={() => {
                setRejectReason('');
                setRejectError(null);
                setIsRejectOpen(true);
              }}
              disabled={isConfirming || isRejecting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold border border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer"
            >
              <XCircle className="w-4 h-4" />
              <span>Reject</span>
            </button>

            <button
              type="button"
              onClick={handleConfirm}
              disabled={isConfirming || isRejecting || (unmappedRequiredFields.length > 0 && !confirmProceedWithMissing)}
              title={
                unmappedRequiredFields.length > 0 && !confirmProceedWithMissing
                  ? `Required fields [${unmappedRequiredFields.join(', ')}] not mapped`
                  : undefined
              }
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold bg-helios-accent-blue hover:bg-blue-600 text-white shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isConfirming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Running Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Approve & Run</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Reject Modal Dialog */}
      {isRejectOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-helios-card-light dark:bg-helios-card-dark rounded-2xl shadow-2xl border border-rose-500/30 overflow-hidden">
            <div className="px-6 py-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between bg-rose-500/5">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-500" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Reject Batch
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsRejectOpen(false)}
                disabled={isRejecting}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleReject} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Reason for Rejection * (min 5 characters)
                </label>
                <textarea
                  rows={4}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Provide the reason for rejection (e.g., Unreadable header format, corrupted file structure, mismatched tenant data)..."
                  className="w-full p-3 text-xs rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-rose-500 resize-none font-sans"
                  required
                  autoFocus
                />
              </div>

              {rejectError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-medium">
                  {rejectError}
                </div>
              )}

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setIsRejectOpen(false)}
                  disabled={isRejecting}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRejecting || rejectReason.trim().length < 5}
                  className="inline-flex items-center justify-center gap-1.5 px-5 py-2 text-xs font-bold rounded-xl bg-rose-600 hover:bg-rose-700 text-white shadow-md transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isRejecting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Rejecting...</span>
                    </>
                  ) : (
                    <span>Confirm Rejection</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>

  );
};

export default ConfirmSchema;
