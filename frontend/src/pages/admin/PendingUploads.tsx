import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  FileText,
  Database,
  Key,
  UploadCloud,
  ArrowRight,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { PendingUpload, SourceType } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { Pagination } from '@/components/ui/Pagination';

export const PendingUploads: React.FC = () => {
  const navigate = useNavigate();
  const [uploads, setUploads] = useState<PendingUpload[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  const loadUploads = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminService.getPendingUploads();
      setUploads(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch pending uploads.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, sourceFilter]);

  const filteredUploads = useMemo(() => {
    return uploads.filter((item) => {
      const matchesSource =
        sourceFilter === 'all' || item.source_type === sourceFilter;
      const matchesSearch =
        searchQuery === '' ||
        item.batch_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.tenant_name && item.tenant_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        item.filename.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSource && matchesSearch;
    });
  }, [uploads, sourceFilter, searchQuery]);

  const renderSourceTypeBadge = (type: SourceType) => {
    switch (type) {
      case 'upload':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <UploadCloud className="w-3 h-3" />
            <span>File Upload</span>
          </span>
        );
      case 'db_connection':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <Database className="w-3 h-3" />
            <span>Database</span>
          </span>
        );
      case 'api_push':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <Key className="w-3 h-3" />
            <span>API Push</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/10 text-slate-400">
            {type}
          </span>
        );
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${bytes} B`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Pending Ingestion Approvals
          </h1>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Review inferred schemas, verify column mappings, and authorize bronze data to transition to Silver Delta tables.
          </p>
        </div>

        <button
          type="button"
          onClick={loadUploads}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-helios-accent-blue' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Batch ID, organization, or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-400">Source:</span>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          >
            <option value="all">All Sources</option>
            <option value="upload">File Uploads</option>
            <option value="db_connection">Database Connectors</option>
            <option value="api_push">API Stream</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={loadUploads} className="underline font-bold">
            Retry
          </button>
        </div>
      )}

      {/* Main Table Container */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : filteredUploads.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No Pending Batches
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              All incoming ingestion batches have been processed, confirmed, or routed to Silver/Gold Delta tables.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                  <th className="py-3 px-4 font-semibold">Batch ID</th>
                  <th className="py-3 px-4 font-semibold">Organization</th>
                  <th className="py-3 px-4 font-semibold">Source Type</th>
                  <th className="py-3 px-4 font-semibold">Dataset / File</th>
                  <th className="py-3 px-4 font-semibold">Rows / Size</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Received</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {filteredUploads
                  .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                  .map((upl: PendingUpload) => {
                    const isPreparing = upl.status === 'ingesting';
                    return (
                      <tr
                        key={upl.batch_id}
                        className={`transition-colors ${
                          isPreparing
                            ? 'opacity-80 bg-black/[0.01] dark:bg-white/[0.01] cursor-not-allowed'
                            : 'hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer group'
                        }`}
                        onClick={() => {
                          if (!isPreparing) {
                            navigate(`/admin/confirm-schema/${upl.batch_id}`);
                          }
                        }}
                      >
                        <td className="py-3.5 px-4 font-mono text-helios-accent-blue font-bold">
                          {upl.batch_id}
                        </td>
                        <td className="py-3.5 px-4 font-medium">
                          {upl.tenant_name || `Organization #${upl.tenant_id}`}
                        </td>
                        <td className="py-3.5 px-4">
                          {renderSourceTypeBadge(upl.source_type)}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-1.5 font-mono text-slate-600 dark:text-slate-300">
                            <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate max-w-[200px]" title={upl.filename}>
                              {upl.filename}
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="font-semibold">{upl.row_count.toLocaleString()}</span> rows
                          {upl.file_size_bytes && (
                            <span className="text-slate-400 ml-1">
                              ({formatFileSize(upl.file_size_bytes)})
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          {isPreparing ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              <span>Preparing</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                              <span>Pending Review</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 shrink-0" />
                            <span>{new Date(upl.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            disabled={isPreparing}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!isPreparing) {
                                navigate(`/admin/confirm-schema/${upl.batch_id}`);
                              }
                            }}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                              isPreparing
                                ? 'opacity-40 cursor-not-allowed bg-slate-500/20 text-slate-400'
                                : 'bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm'
                            }`}
                            title={isPreparing ? 'Preparing batch: Bronze ingestion and schema inference running' : 'Review & Confirm'}
                          >
                            <span>{isPreparing ? 'Preparing...' : 'Review & Confirm'}</span>
                            {!isPreparing && <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>

            </table>
          </div>
          <Pagination
            currentPage={currentPage}
            totalItems={filteredUploads.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        </>
      )}
      </div>
    </div>
  );
};

export default PendingUploads;
