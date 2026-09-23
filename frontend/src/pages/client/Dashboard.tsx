import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Database,
  Loader2,
  PlusCircle,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { ExportButton } from '@/components/client/ExportButton';
import { RevenueTrendChart } from '@/components/dashboard/RevenueTrendChart';
import { TopProductsWidget } from '@/components/dashboard/TopProductsWidget';
import { LateDeliveryWidget } from '@/components/dashboard/LateDeliveryWidget';
import { DiscountProfitWidget } from '@/components/dashboard/DiscountProfitWidget';
import { ShippingModeWidget } from '@/components/dashboard/ShippingModeWidget';
import { dashboardService } from '@/services/dashboardService';
import { DashboardData } from '@/types/dashboard';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<DashboardData>({
    revenueTrend: null,
    topProducts: null,
    lateDeliveryRisk: null,
    discountVsProfit: null,
    shippingModes: null,
    uploadStatus: null,
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Parallel data fetching across all Gold dashboard endpoints
  const loadDashboardData = async (lookbackDays: number, isBackground: boolean = false) => {
    if (isBackground) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const result = await dashboardService.fetchAllDashboardData(lookbackDays);
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard telemetry.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData(days, false);
  }, [days]);

  // Determine if tenant has any data yet
  const hasAnyData = useMemo(() => {
    const hasTrend = (data.revenueTrend?.points || []).length > 0;
    const hasProducts = (data.topProducts?.products || []).length > 0;
    const hasShipments = (data.lateDeliveryRisk?.total_shipments || 0) > 0;
    const hasBands = (data.discountVsProfit?.bands || []).length > 0;
    return hasTrend || hasProducts || hasShipments || hasBands;
  }, [data]);

  // Simplified status formatting (never exposes pipeline internals)
  const renderSimplifiedStatusBadge = () => {
    const statusObj = data.uploadStatus;
    if (!statusObj) return null;

    const normStatus = (statusObj.stage || statusObj.status || '').toLowerCase();

    if (normStatus.includes('fail') || normStatus.includes('error')) {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
          title={statusObj.status}
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
          <span>Status: Action Required — Check file</span>
        </span>
      );
    }

    if (normStatus.includes('process') || normStatus.includes('sync')) {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
          title={statusObj.status}
        >
          <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
          <span>Status: Synchronizing Data...</span>
        </span>
      );
    }

    return (
      <span
        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
        title="All source data is up to date"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>Status: Ready</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Action Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Store Performance & Analytics
            </h1>
            {renderSimplifiedStatusBadge()}
          </div>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Gold-layer dimensional metrics scoped to <strong>{user?.name || 'Your Store'}</strong>. Updated automatically with live ingestion.
          </p>
        </div>

        {/* Action Controls: Refresh + Export */}
        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <button
            type="button"
            onClick={() => loadDashboardData(days, true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50"
            title="Refresh dashboard metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-helios-accent-blue' : ''}`} />
            <span>{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
          </button>

          {/* Export Feature Dropdown */}
          <ExportButton defaultReportType="full_dashboard" />
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadDashboardData(days, false)}
            className="font-bold underline ml-4 hover:opacity-80"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State Banner (if no data has been connected/synced yet) */}
      {!isLoading && !hasAnyData && (
        <div className="p-8 rounded-2xl border-2 border-dashed border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-center space-y-4 shadow-sm animate-fadeIn">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue">
            <Database className="w-7 h-7" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Connect a data source to see insights
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1.5 leading-relaxed">
              You haven't synchronized any sales or order data yet. Upload a spreadsheet, connect a live database, or use the ingestion API to populate your private lakehouse.
            </p>
          </div>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => navigate('/client/select-source')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-helios-accent-blue text-white hover:bg-blue-600 transition-all shadow-md"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Connect Ingestion Source</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* DASHBOARD LAYOUT */}
      <div className="space-y-6">
        {/* ROW 1: Revenue Trend (Full Width) with Export button nearby */}
        <div>
          <RevenueTrendChart
            data={data.revenueTrend}
            isLoading={isLoading}
            selectedDays={days}
            onDaysChange={setDays}
          />
        </div>

        {/* ROW 2: Top Products (50%) | Late Delivery Risk (50%) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopProductsWidget
            data={data.topProducts}
            isLoading={isLoading}
          />
          <LateDeliveryWidget
            data={data.lateDeliveryRisk}
            isLoading={isLoading}
          />
        </div>

        {/* ROW 3: Discount vs Profit (50%) | Shipping Mode Comparison (50%) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DiscountProfitWidget
            data={data.discountVsProfit}
            isLoading={isLoading}
          />
          <ShippingModeWidget
            data={data.shippingModes}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
