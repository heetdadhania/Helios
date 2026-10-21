import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  IndianRupee,
  ShoppingCart,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Database,
  BarChart3,
  Calendar,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { dashboardService } from '@/services/dashboardService';
import { DashboardSummaryResponse } from '@/types/dashboard';
import { formatINR, formatCountIN } from '@/utils/currency';
import { ContactSupportButton } from '@/components/client/ContactSupportButton';
import { useAuth } from '@/hooks/useAuth';

export const ClientHome: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [data, setData] = useState<DashboardSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await dashboardService.getSummary();
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load organization overview metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const renderStatusBadge = (status: string | null) => {
    if (!status) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
          <Clock className="w-3.5 h-3.5" />
          No Submissions Yet
        </span>
      );
    }

    if (status.toLowerCase().includes('ready')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Ready
        </span>
      );
    }

    if (status.toLowerCase().includes('processing')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800 animate-pulse">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          Processing
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
        <AlertTriangle className="w-3.5 h-3.5" />
        Needs attention - please resend
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero Header */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition-colors">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-helios-accent-blue">
                Organization Portal
              </span>
              <span className="text-gray-300 dark:text-gray-700">·</span>
              <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                {user?.business_name || 'Organization Overview'}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Home
            </h1>
            <p className="text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-helios-accent-blue" />
              <span>Data as of:</span>
              <strong className="text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {data?.data_as_of || 'Not Available'}
              </strong>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Latest Submission Status */}
            <div className="flex items-center gap-2 mr-2">
              <span className="text-xs font-medium text-helios-text-secondary-light dark:text-helios-text-secondary-dark hidden sm:inline">
                Latest Submission:
              </span>
              {renderStatusBadge(data?.latest_submission_status ?? null)}
            </div>

            {/* Shortcuts */}
            <ContactSupportButton variant="button" />

            <button
              type="button"
              onClick={() => navigate('/client/dashboard')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-helios-bg-light dark:hover:bg-helios-bg-dark transition shadow-xs"
            >
              <BarChart3 className="w-4 h-4 text-helios-accent-blue" />
              <span>Go to Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="p-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-helios-accent-blue mb-3" />
          <p className="text-sm font-medium">Loading organization summary...</p>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
          <button
            type="button"
            onClick={fetchSummary}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State when no data */}
      {!loading && !error && (!data?.has_data || data?.order_count === 0) && (
        <div className="p-12 rounded-2xl border-2 border-dashed border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-center space-y-4">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue">
            <Database className="w-7 h-7" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No data yet for this organization.
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1.5 leading-relaxed">
              Your organization does not have any processed sales or order records yet. Your assigned operations team will upload and process data batches for you.
            </p>
          </div>
          <div className="pt-2 flex justify-center">
            <ContactSupportButton variant="button" />
          </div>
        </div>
      )}

      {/* Four KPI Figures */}
      {!loading && !error && data?.has_data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* 1. Total Revenue */}
          <div className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Total Revenue
              </span>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <IndianRupee className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {formatINR(data.total_revenue)}
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Cumulative sales revenue
              </p>
            </div>
          </div>

          {/* 2. Order Count */}
          <div className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Order Count
              </span>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <ShoppingCart className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {formatCountIN(data.order_count)}
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Total processed orders
              </p>
            </div>
          </div>

          {/* 3. Late Delivery Percentage */}
          <div className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Late Delivery Rate
              </span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {typeof data.late_delivery_percentage === 'number'
                  ? `${data.late_delivery_percentage.toFixed(1)}%`
                  : '0.0%'}
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Shipments exceeding SLA window
              </p>
            </div>
          </div>

          {/* 4. Average Order Value */}
          <div className="p-5 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs transition hover:shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Average Order Value
              </span>
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {formatINR(data.average_order_value)}
              </div>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Mean revenue per order
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Card to Full Dashboard */}
      {!loading && !error && data?.has_data && (
        <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Deep-Dive Analytics & Visualizations
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              Explore revenue time-series trends, top-selling SKUs, delivery risk channels, and discount profitability.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/client/dashboard')}
            className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-sm"
          >
            <span>Open Full Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
