import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, Play } from 'lucide-react';
import { DataQualityCheck } from '@/types/data';

const qualityRules: DataQualityCheck[] = [
  {
    id: 'qc_1',
    tableName: 'orders_stream_v2',
    tenantSlug: 'acme_retail',
    nullRatePercentage: 0.04,
    duplicateCount: 0,
    schemaMatch: true,
    score: 99.8,
  },
  {
    id: 'qc_2',
    tableName: 'customer_events_raw',
    tenantSlug: 'nordic_outfitters',
    nullRatePercentage: 1.25,
    duplicateCount: 14,
    schemaMatch: true,
    score: 96.4,
  },
  {
    id: 'qc_3',
    tableName: 'product_catalog_sync',
    tenantSlug: 'apex_direct',
    nullRatePercentage: 3.80,
    duplicateCount: 3,
    schemaMatch: false,
    score: 89.2,
  },
];

export const DataQualityPage: React.FC = () => {
  const [runningFix, setRunningFix] = useState<string | null>(null);

  const handleRunCleaning = (id: string) => {
    setRunningFix(id);
    setTimeout(() => {
      setRunningFix(null);
      alert('Data cleaning and null imputation applied successfully to Delta Lake table.');
    }, 1000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Data Quality & Hygiene Engine
        </h2>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
          Automated schema drift detection, null rate thresholding, and Delta table consistency scores.
        </p>
      </div>

      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">Delta Table</th>
                <th className="pb-3 font-semibold">Tenant Slug</th>
                <th className="pb-3 font-semibold">Schema Status</th>
                <th className="pb-3 font-semibold">Null Rate</th>
                <th className="pb-3 font-semibold">Duplicates</th>
                <th className="pb-3 font-semibold">Quality Score</th>
                <th className="pb-3 font-semibold text-right">Sanitize</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {qualityRules.map((q) => (
                <tr key={q.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3.5 font-mono text-helios-accent-blue font-medium">{q.tableName}</td>
                  <td className="py-3.5">{q.tenantSlug}</td>
                  <td className="py-3.5">
                    {q.schemaMatch ? (
                      <span className="flex items-center gap-1 text-helios-accent-teal font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Consistent</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-helios-warning font-medium">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>Drift Detected</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 font-mono">{q.nullRatePercentage}%</td>
                  <td className="py-3.5 font-mono">{q.duplicateCount} rows</td>
                  <td className="py-3.5">
                    <span
                      className={`font-bold font-mono ${
                        q.score >= 95 ? 'text-helios-accent-teal' : 'text-helios-warning'
                      }`}
                    >
                      {q.score} / 100
                    </span>
                  </td>
                  <td className="py-3.5 text-right">
                    <button
                      type="button"
                      onClick={() => handleRunCleaning(q.id)}
                      disabled={runningFix === q.id}
                      className="px-2.5 py-1 rounded-control bg-helios-accent-blue hover:bg-blue-600 text-white font-medium text-xs inline-flex items-center gap-1 transition-colors disabled:opacity-50"
                    >
                      <Play className="w-3 h-3" />
                      <span>{runningFix === q.id ? 'Fixing...' : 'Auto-Clean'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
