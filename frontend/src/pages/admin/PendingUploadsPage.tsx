import React, { useState } from 'react';
import { Check, X, Clock, FileText } from 'lucide-react';
import { PendingUpload } from '@/types/data';

const initialUploads: PendingUpload[] = [
  {
    id: 'upl_101',
    tenantName: 'Acme Retail Group',
    datasetName: 'q3_holiday_transactions.csv',
    rowCount: 245000,
    fileSize: '42.8 MB',
    uploadedAt: '12 mins ago',
    status: 'pending',
  },
  {
    id: 'upl_102',
    tenantName: 'Nordic Outfitters',
    datasetName: 'customer_loyalty_batch.json',
    rowCount: 82100,
    fileSize: '14.2 MB',
    uploadedAt: '45 mins ago',
    status: 'pending',
  },
  {
    id: 'upl_103',
    tenantName: 'Apex Direct Co.',
    datasetName: 'inventory_adjustments.parquet',
    rowCount: 18900,
    fileSize: '3.1 MB',
    uploadedAt: '2 hours ago',
    status: 'pending',
  },
];

export const PendingUploadsPage: React.FC = () => {
  const [uploads, setUploads] = useState<PendingUpload[]>(initialUploads);

  const handleAction = (id: string, newStatus: 'approved' | 'rejected') => {
    setUploads((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: newStatus } : item))
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Pending Ingestion Approvals
        </h2>
        <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
          Review schema validations and authorize raw data to be committed to Unity Catalog Delta tables.
        </p>
      </div>

      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">Tenant Account</th>
                <th className="pb-3 font-semibold">Dataset File</th>
                <th className="pb-3 font-semibold">Rows / Size</th>
                <th className="pb-3 font-semibold">Received</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {uploads.map((upl) => (
                <tr key={upl.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3.5 font-medium">{upl.tenantName}</td>
                  <td className="py-3.5">
                    <div className="flex items-center gap-2 font-mono text-helios-accent-blue">
                      <FileText className="w-4 h-4 shrink-0" />
                      <span>{upl.datasetName}</span>
                    </div>
                  </td>
                  <td className="py-3.5">
                    {upl.rowCount.toLocaleString()} rows{' '}
                    <span className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark">({upl.fileSize})</span>
                  </td>
                  <td className="py-3.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{upl.uploadedAt}</span>
                  </td>
                  <td className="py-3.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize ${
                        upl.status === 'approved'
                          ? 'bg-emerald-500/10 text-helios-accent-teal'
                          : upl.status === 'rejected'
                          ? 'bg-red-500/10 text-helios-error'
                          : 'bg-amber-500/10 text-amber-500'
                      }`}
                    >
                      {upl.status}
                    </span>
                  </td>
                  <td className="py-3.5 text-right">
                    {upl.status === 'pending' ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => handleAction(upl.id, 'approved')}
                          className="px-2.5 py-1 rounded-control bg-helios-accent-teal hover:bg-emerald-600 text-white font-medium text-xs flex items-center gap-1 transition-colors"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAction(upl.id, 'rejected')}
                          className="px-2.5 py-1 rounded-control bg-red-500/10 hover:bg-red-500/20 text-helios-error font-medium text-xs flex items-center gap-1 transition-colors"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>
                    ) : (
                      <span className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        Processed
                      </span>
                    )}
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
