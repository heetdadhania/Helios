import React, { useEffect, useState } from 'react';
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
} from 'lucide-react';
import { SchemaPreview, SourceType } from '@/types/admin';
import { adminService } from '@/services/adminService';

export const ConfirmSchema: React.FC = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();

  const [preview, setPreview] = useState<SchemaPreview | null>(null);
  const [columnOverrides, setColumnOverrides] = useState<Record<string, string>>({});
  const [silverTable, setSilverTable] = useState<string>('silver.fact_orders');
  const [notes, setNotes] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<{ runId: string } | null>(null);

  useEffect(() => {
    if (!batchId) return;
    const fetchPreview = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await adminService.getPreview(batchId);
        setPreview(data);
        setSilverTable(data.suggested_silver_table || 'silver.fact_orders');
        const initialOverrides: Record<string, string> = {};
        data.column_mappings.forEach((mapping) => {
          initialOverrides[mapping.source_column] = mapping.target_column;
        });
        setColumnOverrides(initialOverrides);
      } catch (err: any) {
        setError(err.message || 'Failed to load schema preview.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPreview();
  }, [batchId]);

  const handleTargetChange = (sourceCol: string, targetCol: string) => {
    setColumnOverrides((prev) => ({
      ...prev,
      [sourceCol]: targetCol,
    }));
  };

  const handleConfirm = async () => {
    if (!batchId) return;
    setIsConfirming(true);
    setError(null);
    try {
      const res = await adminService.confirmUpload(batchId, {
        column_mappings: columnOverrides,
        silver_table: silverTable,
        notes: notes || undefined,
      });
      setSuccessResult({ runId: res.silver_job_run_id });
    } catch (err: any) {
      setError(err.message || 'Failed to confirm schema mapping.');
    } finally {
      setIsConfirming(false);
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

        <div className="flex items-center gap-2">
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
          <div className="text-sm font-mono font-bold text-helios-accent-teal mt-1">
            {preview?.confidence_score}%
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
                <th className="py-2.5 px-4 font-semibold">Confidence</th>
                <th className="py-2.5 px-4 font-semibold">Nullable</th>
                <th className="py-2.5 px-4 font-semibold">Target Silver Column</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {(preview?.column_mappings || []).map((col) => (
                <tr key={col.source_column} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-slate-700 dark:text-slate-200">
                    {col.source_column}
                  </td>
                  <td className="py-3 px-4 font-mono text-helios-accent-blue text-[11px]">
                    {col.inferred_type}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        col.confidence_score >= 0.95
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                          : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {Math.round(col.confidence_score * 100)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-400">
                    {col.is_nullable ? 'Nullable' : 'Required'}
                  </td>
                  <td className="py-3 px-4">
                    <input
                      type="text"
                      value={columnOverrides[col.source_column] || ''}
                      onChange={(e) => handleTargetChange(col.source_column, e.target.value)}
                      className="w-48 px-2 py-1 text-xs font-mono rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sample Bronze Rows Preview */}
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

      {/* Confirmation Action Section */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1">
            Audit / Confirmation Notes (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Verified order_date timestamp format with merchant ERP team"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 text-xs rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <p className="text-xs text-slate-400">
            Confirming this schema records an immutable audit log and dispatches the Databricks Silver cleaning job.
          </p>

          <button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirming}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold bg-helios-accent-blue hover:bg-blue-600 text-white shadow-md transition-all disabled:opacity-50"
          >
            {isConfirming ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Triggering Silver Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Confirm Schema & Trigger Silver</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmSchema;
