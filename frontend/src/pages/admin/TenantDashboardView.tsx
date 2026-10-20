import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  Check,
  Code,
  Copy,
  Database,
  Eye,
  Layers,
  RefreshCw,
} from 'lucide-react';
import { oversightService } from '@/services/oversightService';
import { TenantDashboardViewAs } from '@/types/oversight';
import { RevenueTrendChart } from '@/components/dashboard/RevenueTrendChart';
import { TopProductsWidget } from '@/components/dashboard/TopProductsWidget';
import { LateDeliveryWidget } from '@/components/dashboard/LateDeliveryWidget';
import { DiscountProfitWidget } from '@/components/dashboard/DiscountProfitWidget';
import { ShippingModeWidget } from '@/components/dashboard/ShippingModeWidget';
import { formatDateAsOf } from '@/utils/formatters';

interface DashboardError {
  status?: number;
  title: string;
  message: string;
  detail?: string;
  endpoint?: string;
}

export const TenantDashboardView: React.FC = () => {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();

  const [selectedDays, setSelectedDays] = useState<number>(30);
  const [data, setData] = useState<TenantDashboardViewAs | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<DashboardError | null>(null);
  const [copiedError, setCopiedError] = useState<boolean>(false);

  // Validate and parse tenantId
  const parsedTenantId = useMemo(() => {
    if (!tenantId) return null;
    const num = Number(tenantId);
    return isNaN(num) ? null : num;
  }, [tenantId]);

  const fetchDashboard = async (days: number, isBackground: boolean = false) => {
    if (parsedTenantId === null) {
      setError({
        title: 'Invalid Organization Identifier',
        message: `The provided organization identifier "${tenantId}" is invalid. Expected a numeric organization ID.`,
        endpoint: `/oversight/dashboard/${tenantId}`,
      });
      setIsLoading(false);
      return;
    }

    if (isBackground) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const result = await oversightService.getTenantDashboard(parsedTenantId, days);
      setData(result);
    } catch (err: any) {
      const statusCode = err?.response?.status;
      const rawDetail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'An unexpected error occurred while loading organization telemetry.';

      const detailString =
        typeof rawDetail === 'object'
          ? JSON.stringify(rawDetail, null, 2)
          : String(rawDetail);

      let title = 'Unable to Load Organization Telemetry';
      let message = 'Failed to retrieve Gold layer analytical metrics for this organization.';

      if (statusCode === 404) {
        title = 'Organization Not Found';
        message = `Organization #${parsedTenantId} does not exist in the platform registry. The organization may have been removed.`;
      } else if (statusCode === 403) {
        title = 'Access Denied';
        message = 'Administrator privileges are required to view customer analytics in View-As mode.';
      } else if (statusCode === 500) {
        title = 'Lakehouse Query Error';
        message = `The Databricks Gold telemetry service encountered an error executing analytical queries for Organization #${parsedTenantId}.`;
      } else if (err?.code === 'ERR_NETWORK' || !err?.response) {
        title = 'Network Connection Failure';
        message = 'Could not establish connection to the Helios backend API service.';
      }

      setError({
        status: statusCode,
        title,
        message,
        detail: detailString,
        endpoint: `/api/oversight/dashboard/${parsedTenantId}?days=${days}`,
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard(selectedDays, false);
  }, [parsedTenantId, selectedDays]);

  const handleDaysChange = (newDays: number) => {
    setSelectedDays(newDays);
  };

  const copyErrorDetails = () => {
    if (!error) return;
    const errorPayload = [
      `Error Title: ${error.title}`,
      `HTTP Status: ${error.status || 'N/A'}`,
      `Endpoint: ${error.endpoint || 'N/A'}`,
      `Message: ${error.message}`,
      `Technical Detail:\n${error.detail || 'None provided'}`,
    ].join('\n');

    navigator.clipboard.writeText(errorPayload);
    setCopiedError(true);
    setTimeout(() => setCopiedError(false), 2000);
  };

  // Determine if tenant has any recorded activity in Gold layer
  const hasAnyData = useMemo(() => {
    if (!data) return false;
    const hasTrend = (data.revenue_trend?.points || []).length > 0;
    const hasProducts = (data.top_products?.products || []).length > 0;
    const hasShipments = (data.late_delivery_risk?.total_shipments || 0) > 0;
    const hasBands = (data.discount_vs_profit?.bands || []).length > 0;
    const hasModes = (data.shipping_modes?.modes || []).length > 0;
    return hasTrend || hasProducts || hasShipments || hasBands || hasModes;
  }, [data]);

  // Read data_as_of from the responses
  const dataAsOf = useMemo(() => {
    return (
      data?.data_as_of ??
      data?.revenue_trend?.data_as_of ??
      data?.top_products?.data_as_of ??
      data?.late_delivery_risk?.data_as_of ??
      data?.discount_vs_profit?.data_as_of ??
      data?.shipping_modes?.data_as_of ??
      null
    );
  }, [data]);

  const formattedDataAsOf = useMemo(() => formatDateAsOf(dataAsOf), [dataAsOf]);

  return (
    <div className="space-y-6">
      {/* Top Banner / Breadcrumb & Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-helios-border-light dark:border-helios-border-dark">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/tenants')}
            className="p-2 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-slate-500 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark transition-colors"
            title="Back to Organizations List"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-helios-accent-blue/10 text-helios-accent-blue border border-helios-accent-blue/20">
                <Eye className="w-3.5 h-3.5" />
                <span>Admin View-As Mode</span>
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Organization #{parsedTenantId ?? tenantId}
              </span>
              {formattedDataAsOf && (
                <>
                  <span className="text-slate-400 dark:text-slate-600 text-xs">•</span>
                  <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-medium">
                    Data as of {formattedDataAsOf}
                  </span>
                </>
              )}
            </div>
            <h1 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mt-1 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-helios-accent-blue" />
              <span>{data?.tenant_name || `Organization #${tenantId}`}</span>
            </h1>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Day range selectors */}
          <div className="flex items-center bg-helios-card-light dark:bg-helios-card-dark rounded-xl border border-helios-border-light dark:border-helios-border-dark p-1">
            {[
              { val: 7, label: '7d' },
              { val: 30, label: '30d' },
              { val: 0, label: 'All' },
            ].map((d) => (
              <button
                key={d.val}
                onClick={() => handleDaysChange(d.val)}
                disabled={isLoading}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                  selectedDays === d.val
                    ? 'bg-helios-accent-blue text-white shadow-sm'
                    : 'text-slate-500 hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => fetchDashboard(selectedDays, true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-helios-accent-blue' : ''}`}
            />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>

          <Link
            to="/admin/oversight/health"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-slate-600 dark:text-slate-300 hover:border-helios-accent-blue/50 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-helios-accent-blue" />
            <span>Organization Health</span>
          </Link>
        </div>
      </div>

      {/* DISTINCT ERROR STATE */}
      {error ? (
        <div className="p-6 rounded-2xl bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/30 space-y-4 shadow-sm animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 shrink-0 mt-0.5">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-rose-600 dark:text-rose-400">
                    {error.title}
                  </h3>
                  {error.status && (
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                      HTTP {error.status}
                    </span>
                  )}
                </div>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                  {error.message}
                </p>
                {error.endpoint && (
                  <p className="text-[11px] font-mono text-slate-400 mt-1">
                    Target Endpoint: <span className="text-slate-500 dark:text-slate-300">{error.endpoint}</span>
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
              <button
                type="button"
                onClick={copyErrorDetails}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-slate-600 dark:text-slate-300 hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                title="Copy error details for diagnostics"
              >
                {copiedError ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span className="text-emerald-500">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Diagnostics</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => fetchDashboard(selectedDays, false)}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition-colors shadow-sm"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Retry Telemetry</span>
              </button>
            </div>
          </div>

          {/* Detailed Error Diagnostics Box */}
          {error.detail && (
            <div className="space-y-2 pt-2 border-t border-rose-500/20">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-600 dark:text-rose-400">
                <Code className="w-3.5 h-3.5" />
                <span>Technical Diagnostic Trace:</span>
              </div>
              <pre className="p-3.5 rounded-xl bg-black/50 dark:bg-black/60 text-rose-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap leading-relaxed border border-rose-500/20 max-h-60">
                {error.detail}
              </pre>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2 text-xs">
            <button
              onClick={() => navigate('/admin/tenants')}
              className="text-helios-accent-blue hover:underline font-semibold"
            >
              ← Return to Organizations Directory
            </button>
            <span className="text-slate-400">•</span>
            <Link
              to="/admin/oversight/health"
              className="text-helios-accent-blue hover:underline font-semibold"
            >
              Inspect System Pipeline Health
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* Notice Banner */}
          <div className="p-3.5 rounded-xl bg-helios-accent-blue/5 border border-helios-accent-blue/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-helios-accent-blue">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 flex-shrink-0" />
              <span>
                Viewing client-facing Gold analytics for <strong>{data?.tenant_name || `Organization #${tenantId}`}</strong> across {selectedDays} days. Data reflects verified business intelligence tables.
              </span>
            </div>
            <span className="text-[11px] opacity-75 font-mono">Scope: Gold Layer Fact/Dim</span>
          </div>

          {/* Empty State Banner (if data_as_of is null or tenant genuinely has no Gold data yet) */}
          {!isLoading && (dataAsOf === null || !hasAnyData) && (
            <div className="p-8 rounded-2xl border-2 border-dashed border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-center space-y-3 shadow-sm animate-fadeIn">
              <div className="w-12 h-12 mx-auto rounded-xl bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue">
                <Database className="w-6 h-6" />
              </div>
              <div className="max-w-md mx-auto">
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  No data yet for this business.
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 leading-relaxed">
                  Organization #{parsedTenantId ?? tenantId} has no completed orders or shipments recorded in the Gold layer. Charts are showing zeroed baseline states.
                </p>
              </div>
            </div>
          )}

          {/* REUSED CANONICAL DASHBOARD CHART GRID */}
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
        </>
      )}
    </div>
  );
};

export default TenantDashboardView;
