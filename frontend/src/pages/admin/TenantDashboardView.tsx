import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  Eye,
  RefreshCw,
  AlertCircle,
  Layers,
} from 'lucide-react';
import { oversightService } from '@/services/oversightService';
import { TenantDashboardViewAs } from '@/types/oversight';
import { RevenueTrendChart } from '@/components/dashboard/RevenueTrendChart';
import { TopProductsWidget } from '@/components/dashboard/TopProductsWidget';
import { LateDeliveryWidget } from '@/components/dashboard/LateDeliveryWidget';
import { DiscountProfitWidget } from '@/components/dashboard/DiscountProfitWidget';
import { ShippingModeWidget } from '@/components/dashboard/ShippingModeWidget';

export const TenantDashboardView: React.FC = () => {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();

  const [selectedDays, setSelectedDays] = useState<number>(30);
  const [data, setData] = useState<TenantDashboardViewAs | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async (days: number, isBackground: boolean = false) => {
    if (!tenantId) return;
    if (isBackground) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const result = await oversightService.getTenantDashboard(tenantId, days);
      setData(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load tenant dashboard.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard(selectedDays, false);
  }, [tenantId, selectedDays]);

  const handleDaysChange = (newDays: number) => {
    setSelectedDays(newDays);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Breadcrumb & Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-helios-border-light dark:border-helios-border-dark">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/tenants')}
            className="p-2 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-slate-500 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark transition-colors"
            title="Back to Tenants List"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-helios-accent-blue/10 text-helios-accent-blue border border-helios-accent-blue/20">
                <Eye className="w-3.5 h-3.5" />
                <span>Admin View-As Mode</span>
              </span>
              <span className="text-xs text-slate-400">
                Tenant #{tenantId}
              </span>
            </div>
            <h1 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-1 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-helios-accent-blue" />
              <span>{data?.tenant_name || `Tenant ${tenantId}`}</span>
            </h1>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Day range selectors */}
          <div className="flex items-center bg-helios-card-light dark:bg-helios-card-dark rounded-xl border border-helios-border-light dark:border-helios-border-dark p-1">
            {[7, 30, 90, 365].map((d) => (
              <button
                key={d}
                onClick={() => handleDaysChange(d)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                  selectedDays === d
                    ? 'bg-helios-accent-blue text-white shadow-sm'
                    : 'text-slate-500 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>

          <button
            onClick={() => fetchDashboard(selectedDays, true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-helios-accent-blue' : ''}`}
            />
            <span>Refresh</span>
          </button>

          <Link
            to="/admin/oversight/health"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-slate-600 dark:text-slate-300 hover:border-helios-accent-blue/50 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-helios-accent-blue" />
            <span>Tenant Health</span>
          </Link>
        </div>
      </div>

      {/* Notice Banner */}
      <div className="p-3.5 rounded-xl bg-helios-accent-blue/5 border border-helios-accent-blue/20 flex items-center justify-between text-xs text-helios-accent-blue">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 flex-shrink-0" />
          <span>
            Viewing client-facing Gold analytics for <strong>{data?.tenant_name || `Tenant #${tenantId}`}</strong> across {selectedDays} days. Data reflects verified business intelligence tables.
          </span>
        </div>
        <span className="text-[11px] opacity-75 font-mono">Scope: Gold Layer Fact/Dim</span>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">Unable to load tenant telemetry</p>
            <p className="text-xs opacity-90 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="space-y-6">
        {/* 1. Daily Revenue Trend Chart */}
        <RevenueTrendChart
          data={data?.revenue_trend || null}
          isLoading={isLoading}
          selectedDays={selectedDays}
          onDaysChange={handleDaysChange}
        />

        {/* 2. Top Products & Late Delivery Risks */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopProductsWidget
            data={data?.top_products || null}
            isLoading={isLoading}
          />
          <LateDeliveryWidget
            data={data?.late_delivery_risk || null}
            isLoading={isLoading}
          />
        </div>

        {/* 3. Discount vs Profit & Shipping Mode Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DiscountProfitWidget
            data={data?.discount_vs_profit || null}
            isLoading={isLoading}
          />
          <ShippingModeWidget
            data={data?.shipping_modes || null}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

export default TenantDashboardView;
