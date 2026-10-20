import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  CheckCircle2,
  FileText,
  Building2,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Info,
  X,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { adminService } from '@/services/adminService';
import { Tenant, SchemaPreview } from '@/types/admin';
import api from '@/services/api';
import {
  SessionProgressList,
  SessionProgressItem,
} from '@/components/team/SessionProgressList';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { DuplicateConflictDialog } from '@/components/shared/DuplicateConflictDialog';

export const IngestUpload: React.FC = () => {
  const navigate = useNavigate();
  const { user, role } = useAuth();
  const isAdmin = role === 'admin';

  // Tenant state
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>('');
  const [isLoadingTenants, setIsLoadingTenants] = useState<boolean>(true);
  const [tenantsError, setTenantsError] = useState<string | null>(null);

  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'ready'>('idle');
  const [realPreview, setRealPreview] = useState<SchemaPreview | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);

  // Bulk Entry: Session Progress and inline confirmation state
  const [sessionItems, setSessionItems] = useState<SessionProgressItem[]>([]);
  const [inlineConfirmation, setInlineConfirmation] = useState<string | null>(null);

  // Duplicate conflict dialog state
  const [conflictData, setConflictData] = useState<any | null>(null);
  const [isConflictOpen, setIsConflictOpen] = useState<boolean>(false);
  const [isOverriding, setIsOverriding] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const tenantSelectRef = useRef<HTMLSelectElement | null>(null);

  const loadTenants = useCallback(async () => {
    try {
      setIsLoadingTenants(true);
      setTenantsError(null);
      const data = await adminService.getTenants();

      if (user?.role === 'smb_owner' && user?.tenant_id) {
        const myTenant = data.filter(
          (t) => String(t.tenant_id) === String(user.tenant_id)
        );
        setTenants(myTenant);
        setSelectedTenantId(String(user.tenant_id));
      } else if (isAdmin) {
        setTenants(data);
        if (data.length > 0) {
          setSelectedTenantId(String(data[0].tenant_id));
        }
      } else {
        // Team Member: filter to assigned tenants
        let assigned: string[] = (user as any)?.assigned_tenants;
        if (!assigned) {
          try {
            const members = await adminService.getTeamMembers();
            const me = members.find(
              (m) => m.email === user?.email || m.user_id === String(user?.id)
            );
            if (me?.assigned_tenants) {
              assigned = me.assigned_tenants;
            }
          } catch {
            assigned = [];
          }
        }
        const assignedList = assigned || [];
        const filtered = data.filter(
          (t) => assignedList.includes(String(t.tenant_id)) || assignedList.includes(t.slug)
        );
        setTenants(filtered);
        if (filtered.length > 0) {
          setSelectedTenantId(String(filtered[0].tenant_id));
        }
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err.message || 'Unable to retrieve assigned tenants.';
      setTenantsError(errMsg);
    } finally {
      setIsLoadingTenants(false);
    }
  }, [isAdmin, user]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const selectedTenant = useMemo(() => {
    return tenants.find((t) => String(t.tenant_id) === String(selectedTenantId));
  }, [tenants, selectedTenantId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setRealPreview(null);
      setUploadStatus('ready');
      setFeedbackMessage(null);
      setInlineConfirmation(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setRealPreview(null);
      setUploadStatus('ready');
      setFeedbackMessage(null);
      setInlineConfirmation(null);
    }
  };

  const handleSubmitUpload = async (override: boolean = false, reason: string = '') => {
    if (!selectedTenantId) {
      setFeedbackMessage({
        type: 'error',
        text: 'Please select an organization before submitting file ingestion.',
      });
      return;
    }

    if (!selectedFile) {
      setFeedbackMessage({
        type: 'error',
        text: 'Please choose or drop a file to upload.',
      });
      return;
    }

    const currentTenantName = selectedTenant?.name || `Organization #${selectedTenantId}`;
    const fileLabel = selectedFile.name;

    try {
      if (override) {
        setIsOverriding(true);
      } else {
        setIsSubmitting(true);
      }
      setFeedbackMessage(null);

      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('tenant_id', selectedTenantId);
      if (override) {
        formData.append('override_duplicate', 'true');
        formData.append('override_reason', reason);
      }

      const res = await api.post('/uploads', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const responseBatchId = res.data.batch_id;
      const responseUploadId = res.data.upload_id;
      setIsConflictOpen(false);
      setConflictData(null);

      // Try fetching preview if available from API
      try {
        const previewData = await adminService.getPreview(responseBatchId);
        setRealPreview(previewData);
      } catch {
        // Preview may not be immediately available if inference is running
      }

      // 1. Show inline confirmation: "Submitted for [Tenant Name] ✓"
      setInlineConfirmation(`Submitted for ${currentTenantName} ✓` + (override ? ' (Duplicate Override Audited)' : ''));

      // 2. Append to running Session Progress list
      const newSessionItem: SessionProgressItem = {
        id: responseBatchId,
        tenantName: currentTenantName,
        tenantId: selectedTenantId,
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
        status: override ? 'Overridden ✓' : 'Submitted ✓',
        details: fileLabel,
        batchId: responseBatchId,
        uploadId: responseUploadId,
        type: 'file',
      };
      setSessionItems((prev) => [newSessionItem, ...prev]);

      // 3. Reset file input
      setSelectedFile(null);
      setUploadStatus('idle');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // 4. Re-focus tenant selector, ready for the next tenant
      setTimeout(() => {
        tenantSelectRef.current?.focus();
      }, 100);
    } catch (err: any) {
      if (err?.response?.status === 409) {
        const conflict = err.response.data?.detail || err.response.data;
        if (conflict && (conflict.matched || conflict.overlapping_rows !== undefined)) {
          setConflictData({
            matched: conflict.matched || 'Duplicate submission',
            submitted_by: conflict.submitted_by || 'Unknown',
            submitted_at: conflict.submitted_at || 'Recently',
            batch_id: conflict.batch_id || 'N/A',
            overlapping_rows: conflict.overlapping_rows || 0,
            message: conflict.message,
          });
          setIsConflictOpen(true);
          return;
        }
      }
      const errMsg = err?.response?.data?.detail || err.message || 'File ingestion failed. Please verify the format and tenant assignment.';
      setFeedbackMessage({
        type: 'error',
        text: errMsg,
      });
    } finally {
      setIsSubmitting(false);
      setIsOverriding(false);
    }
  };

  const handleDoneForNow = () => {
    navigate('/admin/uploads');
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2.5">
            <UploadCloud className="w-6 h-6 text-helios-accent-blue" />
            Ingest Data File on Behalf of Organization
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Bulk Entry Mode: Upload CSV or Excel spreadsheets across multiple organizations in succession.
            Each submission registers to the pipeline without leaving this page.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {sessionItems.length > 0 && (
            <button
              type="button"
              id="top-done-for-now-btn"
              onClick={handleDoneForNow}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-control text-xs font-bold bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
            >
              <span>Done for now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark shadow-sm">
            <ShieldCheck className="w-4 h-4 text-helios-accent-teal" />
            <span>Role Guard: Team Member & Admin</span>
          </div>
        </div>
      </div>

      {/* Inline Confirmation ("Submitted for [Tenant Name] ✓") */}
      {inlineConfirmation && (
        <div className="p-4 rounded-control bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-between text-xs animate-in fade-in duration-200">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <div>
              <span className="font-bold text-sm">{inlineConfirmation}</span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Batch queued for pipeline processing. The form has been reset with the organization selector re-focused for your next entry.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDoneForNow}
              className="hidden sm:inline-flex items-center gap-1 text-xs font-bold text-helios-accent-blue hover:underline"
            >
              <span>Done for now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setInlineConfirmation(null)}
              className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Error / Warning Feedback Banner */}
      {feedbackMessage && (
        <div
          className={`p-4 rounded-control text-xs flex items-center justify-between border ${
            feedbackMessage.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
              : 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {feedbackMessage.type === 'error' ? (
              <AlertCircle className="w-5 h-5 shrink-0" />
            ) : (
              <Info className="w-5 h-5 shrink-0" />
            )}
            <span className="font-medium">{feedbackMessage.text}</span>
          </div>

          <button
            type="button"
            onClick={() => setFeedbackMessage(null)}
            className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Tenant Selector Card */}
      <div className="p-5 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <label
                htmlFor="tenant-selector"
                className="block text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark uppercase tracking-wider"
              >
                Target Organization *
              </label>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                {isAdmin
                  ? 'Administrator Mode: You can upload on behalf of any active organization in the platform.'
                  : 'Team Member Mode: Showing organizations currently assigned to your account in platform.team_assignments.'}
              </p>
            </div>
          </div>

          <div className="w-full sm:w-72">
            {isLoadingTenants ? (
              <LoadingSkeleton variant="rectangular" className="h-9 w-full" />
            ) : tenantsError ? (
              <div className="flex items-center justify-between gap-2 text-xs text-rose-500 py-1">
                <span>{tenantsError}</span>
                <button
                  type="button"
                  onClick={loadTenants}
                  className="px-2 py-1 text-xs font-semibold rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400"
                >
                  Retry
                </button>
              </div>
            ) : tenants.length === 0 ? (
              <div className="text-xs text-amber-500 font-medium py-2">
                No assigned organizations found for your account.
              </div>
            ) : (
              <select
                id="tenant-selector"
                ref={tenantSelectRef}
                value={selectedTenantId}
                onChange={(e) => {
                  setSelectedTenantId(e.target.value);
                  setFeedbackMessage(null);
                  setInlineConfirmation(null);
                }}
                className="w-full text-xs font-semibold px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
              >
                {tenants.map((t) => (
                  <option key={t.tenant_id} value={t.tenant_id}>
                    {t.name} ({t.tier} · ID: {t.tenant_id})
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {selectedTenant && (
          <div className="mt-2 pt-3 border-t border-helios-border-light dark:border-helios-border-dark flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5">
              Slug: {selectedTenant.slug}
            </span>
            <span className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5">
              Catalog: {selectedTenant.catalog_name || 'helios_catalog'}.{selectedTenant.schema_name || selectedTenant.slug}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
              ● Active Tenant
            </span>
          </div>
        )}
      </div>

      {/* Upload Drag & Drop Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`cursor-pointer border-2 border-dashed rounded-card p-8 text-center transition-all duration-200 bg-helios-card-light dark:bg-helios-card-dark ${
          isDragging
            ? 'border-helios-accent-blue bg-blue-500/5 ring-4 ring-blue-500/10'
            : 'border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-14 h-14 mx-auto rounded-full bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue mb-3.5 transition-transform hover:scale-105">
          <UploadCloud className="w-7 h-7" />
        </div>

        <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Drag and drop file here, or click to browse
        </h3>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
          Accepts standard tabular <strong>.csv</strong> or <strong>.xlsx</strong> files (up to 10MB)
        </p>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors shadow-sm"
          >
            Select Local File
          </button>
        </div>
      </div>

      {/* Selected File Details */}
      {selectedFile && (
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-helios-border-light dark:border-helios-border-dark pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark font-mono">
                  {selectedFile.name}
                </h4>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Target Organization:{' '}
                  <strong className="text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {selectedTenant?.name || `Organization #${selectedTenantId}`}
                  </strong>{' '}
                  · {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {uploadStatus === 'ready' && (
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-helios-accent-teal border border-emerald-500/20 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Ready to Ingest
                </span>
              )}
            </div>
          </div>

          {/* Real Inferred Schema Preview if returned from API */}
          {realPreview && realPreview.column_mappings && (
            <div className="overflow-x-auto">
              <div className="mb-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Inferred Schema Preview ({realPreview.inferred_template})
              </div>
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider text-[11px]">
                    <th className="pb-2.5 font-semibold">Source Column</th>
                    <th className="pb-2.5 font-semibold">Target Column</th>
                    <th className="pb-2.5 font-semibold">Inferred Type</th>
                    <th className="pb-2.5 font-semibold">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark font-mono">
                  {realPreview.column_mappings.map((col, idx) => (
                    <tr key={idx}>
                      <td className="py-2 text-helios-text-primary-light dark:text-helios-text-primary-dark font-semibold">
                        {col.source_column}
                      </td>
                      <td className="py-2 text-helios-accent-blue font-semibold">
                        {col.target_column}
                      </td>
                      <td className="py-2 text-slate-500 font-sans">
                        {col.inferred_type}
                      </td>
                      <td className="py-2 text-helios-accent-teal font-sans">
                        {Math.round(col.confidence_score * 100)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Action Row */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-helios-border-light dark:border-helios-border-dark">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-helios-accent-blue shrink-0" />
              <span>
                Submitting will land the file into{' '}
                <code className="px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/5 font-mono text-[11px]">
                  /Volumes/helios/bronze/uploads/{selectedTenantId}/
                </code>
              </span>
            </div>

            <button
              type="button"
              id="submit-ingest-btn"
              onClick={() => handleSubmitUpload()}
              disabled={isSubmitting || !selectedTenantId}
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-bold rounded-control bg-helios-accent-teal text-white hover:bg-emerald-600 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Submitting Ingestion...</span>
                </>
              ) : (
                <>
                  <span>Submit & Prepare Next Organization</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Running Session Progress Panel */}
      <SessionProgressList
        items={sessionItems}
        title="Session Progress"
        description="Organizations submitted during this active session without leaving the page"
        onDone={handleDoneForNow}
        doneButtonLabel="Done for now"
        onClear={() => setSessionItems([])}
      />

      <DuplicateConflictDialog
        isOpen={isConflictOpen}
        conflictData={conflictData}
        onClose={() => setIsConflictOpen(false)}
        onOverride={(reason) => handleSubmitUpload(true, reason)}
        isOverriding={isOverriding}
      />
    </div>
  );
};

export default IngestUpload;
