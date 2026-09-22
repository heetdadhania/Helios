import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, FileText, Database, ArrowRight } from 'lucide-react';

export const UploadDataPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<'idle' | 'analyzing' | 'ready'>('idle');

  const handleSimulatedDrop = (fileName: string) => {
    setSelectedFile(fileName);
    setUploadState('analyzing');
    setTimeout(() => {
      setUploadState('ready');
    }, 800);
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

      {/* Upload Box */}
      <div
        onClick={() => handleSimulatedDrop('sample_orders_2026.csv')}
        className="cursor-pointer border-2 border-dashed rounded-card p-8 text-center transition-all duration-200 border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue bg-helios-card-light dark:bg-helios-card-dark"
      >
        <div className="w-12 h-12 mx-auto rounded-full bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue mb-3">
          <UploadCloud className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Click to upload or drag and drop datasets
        </h3>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
          CSV, JSON, or Parquet files up to 500MB
        </p>
        <div className="mt-4">
          <button
            type="button"
            className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
          >
            Select File
          </button>
        </div>
      </div>

      {/* Inferred Schema Preview if uploaded */}
      {selectedFile && (
        <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-helios-accent-blue" />
              <div>
                <h4 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {selectedFile}
                </h4>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  14,280 rows · 4 columns detected
                </p>
              </div>
            </div>
            {uploadState === 'ready' && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-helios-accent-teal flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Schema Inferred
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  <th className="pb-2 font-semibold">Column Name</th>
                  <th className="pb-2 font-semibold">Inferred Type</th>
                  <th className="pb-2 font-semibold">Sample Value</th>
                  <th className="pb-2 font-semibold">Nullability</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                <tr>
                  <td className="py-2.5 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">order_id</td>
                  <td className="py-2.5 text-helios-accent-blue font-mono">string</td>
                  <td className="py-2.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">"ORD-98214"</td>
                  <td className="py-2.5 text-helios-accent-teal">Non-nullable</td>
                </tr>
                <tr>
                  <td className="py-2.5 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">customer_email</td>
                  <td className="py-2.5 text-helios-accent-blue font-mono">string</td>
                  <td className="py-2.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">"buyer@example.com"</td>
                  <td className="py-2.5 text-helios-accent-teal">Non-nullable</td>
                </tr>
                <tr>
                  <td className="py-2.5 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">total_amount</td>
                  <td className="py-2.5 text-helios-accent-blue font-mono">float</td>
                  <td className="py-2.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">142.50</td>
                  <td className="py-2.5 text-amber-500">Nullable (0.2%)</td>
                </tr>
                <tr>
                  <td className="py-2.5 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">ordered_at</td>
                  <td className="py-2.5 text-helios-accent-blue font-mono">datetime</td>
                  <td className="py-2.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">2026-09-22T14:30:00Z</td>
                  <td className="py-2.5 text-helios-accent-teal">Non-nullable</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="button"
              onClick={() => alert('Dataset submitted for Delta Lake transformation.')}
              className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-teal text-white hover:bg-emerald-600 transition-colors flex items-center gap-1.5"
            >
              <span>Submit to Pipeline Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
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
            <button className="text-xs text-helios-accent-blue hover:underline">Connect</button>
          </div>
        </div>
      </div>
    </div>
  );
};
