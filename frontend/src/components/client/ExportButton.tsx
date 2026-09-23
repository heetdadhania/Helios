import React, { useState, useRef, useEffect } from 'react';
import {
  Download,
  FileSpreadsheet,
  FileText,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { exportService, ExportFormat, ReportType } from '@/services/exportService';

interface ExportButtonProps {
  defaultReportType?: ReportType;
  className?: string;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  defaultReportType = 'full_dashboard',
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingFormat, setLoadingFormat] = useState<ExportFormat | null>(null);
  const [reportType, setReportType] = useState<ReportType>(defaultReportType);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleTriggerExport = async (format: ExportFormat) => {
    setIsLoading(true);
    setLoadingFormat(format);
    setFeedback(null);
    setIsOpen(false);

    try {
      await exportService.requestExport({
        report_type: reportType,
        format,
        date_range: { days: 30 },
      });
      setFeedback({
        type: 'success',
        message: `Dashboard ${format.toUpperCase()} exported successfully!`,
      });
      setTimeout(() => setFeedback(null), 4000);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Export failed. Please try again.',
      });
      setTimeout(() => setFeedback(null), 5000);
    } finally {
      setIsLoading(false);
      setLoadingFormat(null);
    }
  };

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      {/* Main Trigger Button */}
      <button
        type="button"
        disabled={isLoading}
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-all shadow-sm disabled:opacity-60"
        title="Export dashboard metrics as CSV or PDF"
      >
        {isLoading ? (
          <Loader2 className="w-3.5 h-3.5 text-helios-accent-blue animate-spin" />
        ) : (
          <Download className="w-3.5 h-3.5 text-helios-accent-blue" />
        )}
        <span>{isLoading ? `Exporting ${loadingFormat?.toUpperCase()}...` : 'Export'}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Floating Status Toast */}
      {feedback && (
        <div
          className={`absolute right-0 top-full mt-2 z-50 flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium shadow-lg border animate-fadeIn whitespace-nowrap ${
            feedback.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-1.5 w-60 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xl p-2 z-50 animate-fadeIn text-xs">
          {/* Report Scope Selector */}
          <div className="px-2 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Export View
          </div>
          <div className="space-y-1 mb-2">
            {[
              { id: 'full_dashboard' as ReportType, label: 'Full Dashboard' },
              { id: 'revenue_trend' as ReportType, label: 'Revenue Trend Only' },
              { id: 'top_products' as ReportType, label: 'Top Products Only' },
            ].map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setReportType(option.id)}
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center justify-between ${
                  reportType === option.id
                    ? 'bg-helios-accent-blue/10 text-helios-accent-blue font-semibold'
                    : 'text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                <span>{option.label}</span>
                {reportType === option.id && <span className="w-1.5 h-1.5 rounded-full bg-helios-accent-blue" />}
              </button>
            ))}
          </div>

          <div className="h-px bg-helios-border-light dark:bg-helios-border-dark my-1" />

          {/* Action Format Buttons */}
          <div className="space-y-1 pt-1">
            <button
              type="button"
              onClick={() => handleTriggerExport('csv')}
              className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors flex items-center gap-2.5 group"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-500 group-hover:scale-110 transition-transform" />
              <div>
                <div className="font-semibold">Export as CSV</div>
                <div className="text-[10px] text-slate-400">Raw rows formatted for Excel/Sheets</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleTriggerExport('pdf')}
              className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors flex items-center gap-2.5 group"
            >
              <FileText className="w-4 h-4 text-rose-500 group-hover:scale-110 transition-transform" />
              <div>
                <div className="font-semibold">Export as PDF</div>
                <div className="text-[10px] text-slate-400">Lightweight printable report with tables</div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExportButton;
