import React, { useState } from 'react';
import { Download, Check } from 'lucide-react';

export const ExportDataPage: React.FC = () => {
  const [selectedFormat, setSelectedFormat] = useState<'csv' | 'parquet' | 'json'>('csv');
  const [selectedTable, setSelectedTable] = useState<string>('orders_stream_v2');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [downloadSuccess, setDownloadSuccess] = useState<boolean>(false);

  const handleTriggerExport = () => {
    setIsExporting(true);
    setDownloadSuccess(false);
    setTimeout(() => {
      setIsExporting(false);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 3000);
    }, 1200);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Export Datasets
        </h2>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
          Extract sanitized tabular data from your Unity Catalog namespace in multiple industry standard formats.
        </p>
      </div>

      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-5">
        {/* Source Table */}
        <div>
          <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1">
            Source Delta Table
          </label>
          <select
            value={selectedTable}
            onChange={(e) => setSelectedTable(e.target.value)}
            className="w-full sm:w-80 px-3 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          >
            <option value="orders_stream_v2">orders_stream_v2 (14,280 rows)</option>
            <option value="customer_events_raw">customer_events_raw (98,400 rows)</option>
            <option value="inventory_snapshots">inventory_snapshots (4,200 rows)</option>
          </select>
        </div>

        {/* Export Format Selector */}
        <div>
          <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-2">
            Output File Format
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { id: 'csv', label: 'CSV (Comma Separated)', desc: 'Universal spreadsheet compatibility' },
              { id: 'parquet', label: 'Apache Parquet', desc: 'Columnar compression for analytics' },
              { id: 'json', label: 'Newline JSON', desc: 'Stream/API consumption' },
            ].map((fmt) => (
              <div
                key={fmt.id}
                onClick={() => setSelectedFormat(fmt.id as any)}
                className={`cursor-pointer p-3.5 rounded-control border text-left transition-all ${
                  selectedFormat === fmt.id
                    ? 'border-helios-accent-blue bg-helios-accent-blue/10'
                    : 'border-helios-border-light dark:border-helios-border-dark hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                <div className="text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark uppercase">
                  {fmt.id}
                </div>
                <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                  {fmt.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Date Filter Range */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1">
              Start Date
            </label>
            <input
              type="date"
              defaultValue="2026-09-01"
              className="w-full px-3 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1">
              End Date
            </label>
            <input
              type="date"
              defaultValue="2026-09-22"
              className="w-full px-3 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
          </div>
        </div>

        {/* Export Button */}
        <div className="pt-2 flex items-center gap-3">
          <button
            type="button"
            onClick={handleTriggerExport}
            disabled={isExporting}
            className="px-5 py-2.5 text-xs font-semibold rounded-control bg-helios-accent-blue hover:bg-blue-600 text-white transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{isExporting ? 'Generating Bundle...' : `Export ${selectedTable}.${selectedFormat}`}</span>
          </button>
          {downloadSuccess && (
            <span className="text-xs text-helios-accent-teal font-medium flex items-center gap-1.5 animate-fade-in">
              <Check className="w-4 h-4" /> Download started
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
