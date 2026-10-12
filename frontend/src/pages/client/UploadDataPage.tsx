import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  CheckCircle2,
  FileText,
  Database,
  ArrowRight,
  AlertCircle,
  RefreshCw,
  X,
} from 'lucide-react';
import api from '@/services/api';
import { SchemaPreview } from '@/types/admin';
import { DuplicateConflictDialog } from '@/components/shared/DuplicateConflictDialog';

export const UploadDataPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [realPreview, setRealPreview] = useState<SchemaPreview | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setRealPreview(null);
      setFeedback(null);
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
      setSelectedFile(e.dataTransfer.files[0]);
      setRealPreview(null);
      setFeedback(null);
    }
  };

  const [conflictData, setConflictData] = useState<any | null>(null);
  const [isConflictOpen, setIsConflictOpen] = useState<boolean>(false);
  const [isOverriding, setIsOverriding] = useState<boolean>(false);

  const handleSubmitUpload = async (override: boolean = false, reason: string = '') => {
    if (!selectedFile) {
      setFeedback({ type: 'error', message: 'Please select a file to upload.' });
      return;
    }

    try {
      if (override) {
        setIsOverriding(true);
      } else {
        setIsSubmitting(true);
      }
      setFeedback(null);

      const formData = new FormData();
      formData.append('file', selectedFile);
      if (override) {
        formData.append('override_duplicate', 'true');
        formData.append('override_reason', reason);
      }

      const res = await api.post('/uploads', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const batchId = res.data.batch_id;
      localStorage.setItem('helios_last_upload_id', String(res.data.upload_id));
      setIsConflictOpen(false);
      setConflictData(null);

      // Attempt to load preview if available
      try {
        const previewRes = await api.get<SchemaPreview>(`/uploads/${batchId}/preview`);
        setRealPreview(previewRes.data);
      } catch {
        // Inferred preview may not be ready immediately
      }

      setFeedback({
        type: 'success',
        message: `Dataset successfully uploaded (Batch ID: ${batchId}). Submitted to pipeline queue.` + (override ? ' (Duplicate Override Audited)' : ''),
      });
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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
      const errMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err.message ||
        'Upload failed. Please verify the file and try again.';
      setFeedback({ type: 'error', message: errMsg });
    } finally {
      setIsSubmitting(false);
      setIsOverriding(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Connect & Ingest Data
        </h2>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
          Ingest raw tabular files or establish managed connectors into your tenant's Unity Catalog schema.
        </p>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-control text-xs flex items-center justify-between border ${
            feedback.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {feedback.type === 'error' ? (
              <AlertCircle className="w-5 h-5 shrink-0" />
            ) : (
              <CheckCircle2 className="w-5 h-5 shrink-0" />
            )}
            <span className="font-medium">{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Upload Box */}
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

        <div className="w-12 h-12 mx-auto rounded-full bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue mb-3">
          <UploadCloud className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Click to upload or drag and drop datasets
        </h3>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
          CSV or Excel (.xlsx) files up to 10MB
        </p>
        <div className="mt-4">
          <button
            type="button"
            className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors shadow-sm"
          >
            Select File
          </button>
        </div>
      </div>

      {/* Selected File Details */}
      {selectedFile && (
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-helios-accent-blue" />
              <div>
                <h4 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark font-mono">
                  {selectedFile.name}
                </h4>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  {(selectedFile.size / 1024).toFixed(1)} KB · Ready to upload
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSelectedFile(null)}
              className="text-xs text-slate-400 hover:text-rose-500"
            >
              Remove
            </button>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="button"
              onClick={handleSubmitUpload}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-teal text-white hover:bg-emerald-600 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <span>Submit to Pipeline Queue</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Real Inferred Schema Preview if returned */}
      {realPreview && realPreview.column_mappings && (
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <div>
                <h4 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Schema Inferred ({realPreview.inferred_template})
                </h4>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  {realPreview.column_mappings.length} columns detected
                </p>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <th className="pb-2 font-semibold">Column Name</th>
                  <th className="pb-2 font-semibold">Inferred Type</th>
                  <th className="pb-2 font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                {realPreview.column_mappings.map((col, idx) => (
                  <tr key={idx}>
                    <td className="py-2.5 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      {col.source_column}
                    </td>
                    <td className="py-2.5 text-helios-accent-blue font-mono">
                      {col.inferred_type}
                    </td>
                    <td className="py-2.5 text-helios-accent-teal font-sans">
                      {Math.round(col.confidence_score * 100)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Available Direct Connectors */}
      <div className="pt-4">
        <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-3">
          Managed Data Connectors
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-emerald-500" />
              <div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">Shopify Store API</div>
                <div className="text-[11px] text-emerald-500">Connected</div>
              </div>
            </div>
            <button className="text-xs text-helios-accent-blue hover:underline">Config</button>
          </div>
          <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-indigo-500" />
              <div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">Stripe Billing</div>
                <div className="text-[11px] text-emerald-500">Connected</div>
              </div>
            </div>
            <button className="text-xs text-helios-accent-blue hover:underline">Config</button>
          </div>
          <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-amber-500" />
              <div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">PostgreSQL Replicate</div>
                <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">Standby</div>
              </div>
            </div>
            <button
              onClick={() => navigate('/client/connect-db')}
              className="text-xs font-semibold text-helios-accent-blue hover:underline"
            >
              Connect
            </button>
          </div>
        </div>
      </div>

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
