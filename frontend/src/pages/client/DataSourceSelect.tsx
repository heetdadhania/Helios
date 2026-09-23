import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  Database,
  Key,
  ArrowRight,
  Sparkles,
  LayoutDashboard,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export const DataSourceSelect: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const sources = [
    {
      id: 'upload',
      title: 'Upload File',
      subtitle: 'Ingest tabular spreadsheets and extracts',
      description:
        'Upload your historical orders, inventory, and shipment data in .csv or .xlsx formats. Automated schema inference and validation starts immediately.',
      route: '/client/upload',
      icon: UploadCloud,
      color: 'blue',
      badge: 'Fastest Setup',
      features: [
        'Supports CSV & Excel (up to 10MB)',
        'Automated type & schema inference',
        'Bronze medallion normalization',
      ],
      buttonText: 'Upload Datasets',
    },
    {
      id: 'database',
      title: 'Connect Database',
      subtitle: 'Continuous synchronization with your transactional database',
      description:
        'Establish direct read replicas with PostgreSQL, MySQL, or SQL Server. Credentials are encrypted in Databricks Secrets and synchronized on a recurring schedule.',
      route: '/client/connect-db',
      icon: Database,
      color: 'emerald',
      badge: 'Live Sync',
      features: [
        'PostgreSQL, MySQL & SQL Server',
        'Encrypted credential storage',
        'Automated incremental sync',
      ],
      buttonText: 'Configure Connector',
    },
    {
      id: 'api',
      title: 'Use API',
      subtitle: 'Stream events directly into your Unity Catalog schema',
      description:
        'Push transactions, order updates, and customer events programmatically via REST. Generate encrypted API keys with per-tenant isolation.',
      route: '/client/api-access',
      icon: Key,
      color: 'purple',
      badge: 'Programmatic',
      features: [
        'REST JSON push endpoints',
        'Cryptographic API key isolation',
        'Real-time streaming ingestion',
      ],
      buttonText: 'Manage API Access',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 py-4">
      {/* Welcome Banner */}
      <div className="text-center max-w-2xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-helios-accent-blue/10 text-helios-accent-blue border border-helios-accent-blue/20">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Tenant Ingestion Hub</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-helios-text-primary-light dark:text-helios-text-primary-dark tracking-tight">
          Select Your Ingestion Source
        </h1>
        <p className="text-xs sm:text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark leading-relaxed">
          Welcome to Helios, <strong>{user?.name || 'Partner'}</strong>. Choose how you want to bring your store's data into your private Unity Catalog medallion lakehouse.
        </p>
      </div>

      {/* 3 Source Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {sources.map((src) => {
          const Icon = src.icon;
          const isBlue = src.color === 'blue';
          const isEmerald = src.color === 'emerald';

          return (
            <div
              key={src.id}
              onClick={() => navigate(src.route)}
              className="group relative flex flex-col justify-between p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue dark:hover:border-helios-accent-blue transition-all duration-300 shadow-sm hover:shadow-xl cursor-pointer overflow-hidden"
            >
              {/* Top Accent Gradient Border */}
              <div
                className={`absolute top-0 left-0 right-0 h-1 transition-opacity ${
                  isBlue
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-500'
                    : isEmerald
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-500'
                    : 'bg-gradient-to-r from-purple-500 to-pink-500'
                }`}
              />

              <div>
                {/* Header Icon & Badge */}
                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 ${
                      isBlue
                        ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                        : isEmerald
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                        : 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                    }`}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-black/5 dark:bg-white/5 text-slate-500 dark:text-slate-400">
                    {src.badge}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark group-hover:text-helios-accent-blue transition-colors">
                  {src.title}
                </h3>
                <p className="text-xs font-medium text-slate-400 mt-0.5">
                  {src.subtitle}
                </p>

                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-3 leading-relaxed">
                  {src.description}
                </p>

                {/* Feature Bullets */}
                <ul className="mt-5 space-y-2 border-t border-helios-border-light dark:border-helios-border-dark pt-4 text-xs">
                  {src.features.map((feat, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Action Button */}
              <div className="mt-6 pt-4 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(src.route);
                  }}
                  className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-sm ${
                    isBlue
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : isEmerald
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      : 'bg-purple-600 hover:bg-purple-700 text-white'
                  }`}
                >
                  <span>{src.buttonText}</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Direct Link to Existing Dashboard */}
      <div className="p-4 rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-helios-border-light dark:border-helios-border-dark flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-400 text-center sm:text-left">
          <LayoutDashboard className="w-4 h-4 text-helios-accent-blue flex-shrink-0" />
          <span>Already have data synchronized with your Unity Catalog schema?</span>
        </div>
        <button
          type="button"
          onClick={() => navigate('/client/dashboard')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark font-semibold hover:bg-black/5 dark:hover:bg-white/5 transition-colors whitespace-nowrap"
        >
          <span>Open Store Dashboard</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

export default DataSourceSelect;
