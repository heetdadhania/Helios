import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  Building2,
  Check,
  IndianRupee,
  Layers,
  Percent,
  RefreshCw,
  Users,
  AlertCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { oversightService } from '@/services/oversightService';
import {
  TenantCompareResponse,
  TenantHealthItem,
} from '@/types/oversight';
import { useTheme } from '@/hooks/useTheme';
import { formatDateAsOf } from '@/utils/formatters';
import { formatINR, formatINRCompact, formatCountIN, formatDateTimeIN } from '@/utils/currency';

export const TenantComparison: React.FC = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [availableTenants, setAvailableTenants] = useState<TenantHealthItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedDays, setSelectedDays] = useState<number>(30);

  const [comparisonData, setComparisonData] = useState<TenantCompareResponse | null>(null);
  const [isLoadingTenants, setIsLoadingTenants] = useState<boolean>(true);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available tenants on mount
  useEffect(() => {
    const fetchTenants = async () => {
      setIsLoadingTenants(true);
      try {
        const res = await oversightService.getTenantHealth();
        setAvailableTenants(res.tenants);
        // Pre-select first 2-3 tenants if available
        if (res.tenants.length >= 2) {
          setSelectedIds([res.tenants[0].tenant_id, res.tenants[1].tenant_id]);
        }
      } catch (err: any) {
        setError(err?.message || 'Could not load tenant directory.');
      } finally {
        setIsLoadingTenants(false);
      }
    };
    fetchTenants();
  }, []);

  // Perform comparison query when selectedIds or selectedDays changes
  const runComparison = async (ids: number[], days: number) => {
    if (ids.length < 2) {
      setComparisonData(null);
      return;
    }
    setIsComparing(true);
    setError(null);
    try {
      const res = await oversightService.compareTenants({
        tenant_ids: ids,
        days: days === 0 ? null : days,
      });
      setComparisonData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to compare selected tenants.');
      setComparisonData(null);
    } finally {
      setIsComparing(false);
    }
  };

  useEffect(() => {
    if (selectedIds.length >= 2) {
      runComparison(selectedIds, selectedDays);
    } else {
      setComparisonData(null);
    }
  }, [selectedIds, selectedDays]);

  const toggleTenant = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedIds(availableTenants.map((t) => t.tenant_id));
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const gridColor = isDark ? '#262626' : '#E5E7EB';
  const textColor = isDark ? '#A3A3A3' : '#6B7280';
  const tooltipBg = isDark ? '#161616' : '#FFFFFF';
  const tooltipBorder = isDark ? '#262626' : '#E5E7EB';

  const chartColors = [
    '#3B82F6', // Blue
    '#10B981', // Emerald
    '#F59E0B', // Amber
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#06B6D4', // Cyan
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-helios-accent-blue" />
            <span>Cross-Organization Performance Comparison</span>
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Benchmark revenue, order sizes, SLA compliance, and fulfillment transit duration across 2 or more organizations.
          </p>
        </div>

        {/* Lookback Filter */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-helios-card-light dark:bg-helios-card-dark rounded-xl border border-helios-border-light dark:border-helios-border-dark p-1">
            {[
              { label: '30d', val: 30 },
              { label: '90d', val: 90 },
              { label: '1 yr', val: 365 },
              { label: 'All', val: 0 },
            ].map((d) => (
              <button
                key={d.val}
                onClick={() => setSelectedDays(d.val)}
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
            onClick={() => runComparison(selectedIds, selectedDays)}
            disabled={isComparing || selectedIds.length < 2}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isComparing ? 'animate-spin text-helios-accent-blue' : ''}`}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tenant Multi-Selector */}
      <div className="p-4 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            <Users className="w-4 h-4 text-helios-accent-blue" />
            <span>Select Organizations to Compare ({selectedIds.length} chosen)</span>
            <span className="text-[11px] font-normal text-slate-400">— minimum 2 required</span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={selectAll}
              className="text-helios-accent-blue hover:underline font-semibold"
            >
              Select All
            </button>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <button
              type="button"
              onClick={clearSelection}
              className="text-slate-500 hover:underline"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Tenant Selection Pills */}
        <div className="flex flex-wrap gap-2 pt-1">
          {isLoadingTenants ? (
            <div className="text-xs text-slate-400 py-2">Loading organizations...</div>
          ) : (
            availableTenants.map((t) => {
              const isSelected = selectedIds.includes(t.tenant_id);
              const compared = comparisonData?.tenants.find((ct) => ct.tenant_id === t.tenant_id);
              const asOf = formatDateAsOf(compared?.data_as_of);
              return (
                <button
                  key={t.tenant_id}
                  type="button"
                  onClick={() => toggleTenant(t.tenant_id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                    isSelected
                      ? 'bg-helios-accent-blue text-white border-helios-accent-blue shadow-sm'
                      : 'bg-black/5 dark:bg-white/5 text-slate-600 dark:text-slate-300 border-helios-border-light dark:border-helios-border-dark hover:border-helios-accent-blue/40'
                  }`}
                >
                  <Building2 className={`w-3.5 h-3.5 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                  <span>{t.tenant_name}</span>
                  {asOf && (
                    <span className={`text-[10px] font-normal ${isSelected ? 'text-white/80' : 'text-slate-400'}`}>
                      ({asOf})
                    </span>
                  )}
                  {isSelected && <Check className="w-3.5 h-3.5 ml-0.5" />}
                </button>
              );
            })
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          {selectedIds.length >= 2 && (
            <button
              onClick={() => runComparison(selectedIds, selectedDays)}
              className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-700 dark:text-rose-300 font-semibold text-[11px] transition-colors flex-shrink-0"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Content depending on selection count and query state */}
      {selectedIds.length < 2 ? (
        <div className="p-16 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-dashed border-helios-border-light dark:border-helios-border-dark text-center space-y-3">
          <BarChart3 className="w-12 h-12 mx-auto text-slate-400 opacity-50" />
          <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Select At Least 2 Organizations
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Choose two or more organizations from the pills above to view comparative gross revenue, shipment SLA reliability, and order unit metrics side-by-side.
          </p>
        </div>
      ) : isComparing ? (
        <div className="p-16 text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-helios-accent-blue mb-3" />
          <p className="text-xs text-slate-500 font-medium">Aggregating comparative telemetry...</p>
        </div>
      ) : error && !comparisonData ? (
        <div className="p-16 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-rose-500/20 text-center space-y-3">
          <AlertCircle className="w-12 h-12 mx-auto text-rose-500 opacity-80" />
          <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Comparison Request Failed
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            An error occurred while compiling side-by-side telemetry for the selected organizations:
          </p>
          <p className="text-xs font-mono text-rose-600 dark:text-rose-400 bg-rose-500/5 border border-rose-500/10 p-2.5 rounded-lg max-w-lg mx-auto">
            {error}
          </p>
          <div className="pt-2">
            <button
              onClick={() => runComparison(selectedIds, selectedDays)}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-helios-accent-blue text-white shadow-sm hover:opacity-90 transition-opacity"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Comparison</span>
            </button>
          </div>
        </div>
      ) : comparisonData ? (
        <div className="space-y-6 animate-fadeIn">
          {/* Side-by-Side Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Comparison Bar Chart */}
            <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                    <IndianRupee className="w-4 h-4 text-emerald-500" />
                    <span>Gross Revenue by Organization (INR)</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">Total completed revenue in selected timeframe</p>
                </div>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={comparisonData.tenants}
                    margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                    <XAxis
                      dataKey="tenant_name"
                      stroke={textColor}
                      fontSize={11}
                      tickLine={false}
                      interval={0}
                      tick={{ fill: textColor }}
                    />
                    <YAxis
                      stroke={textColor}
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(val) => formatINRCompact(val)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        color: isDark ? '#F5F5F5' : '#111827',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      }}
                      itemStyle={{ color: isDark ? '#F5F5F5' : '#111827' }}
                      labelStyle={{ color: isDark ? '#A3A3A3' : '#6B7280' }}
                      formatter={(val: number) => [formatINR(val), 'Total Revenue']}
                    />
                    <Bar dataKey="total_revenue" radius={[6, 6, 0, 0]}>
                      {comparisonData.tenants.map((_entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={chartColors[index % chartColors.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Late Delivery Rate Comparison Bar Chart */}
            <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                    <Percent className="w-4 h-4 text-amber-500" />
                    <span>Late Delivery Breach Rate (%)</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">SLA delivery delay percentage (lower is better)</p>
                </div>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={comparisonData.tenants}
                    margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                    <XAxis
                      dataKey="tenant_name"
                      stroke={textColor}
                      fontSize={11}
                      tickLine={false}
                      interval={0}
                      tick={{ fill: textColor }}
                    />
                    <YAxis
                      stroke={textColor}
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(val) => `${val}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: tooltipBg,
                        borderColor: tooltipBorder,
                        color: isDark ? '#F5F5F5' : '#111827',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      }}
                      itemStyle={{ color: isDark ? '#F5F5F5' : '#111827' }}
                      labelStyle={{ color: isDark ? '#A3A3A3' : '#6B7280' }}
                      formatter={(val: number) => [`${val.toFixed(1)}%`, 'Late Delivery Rate']}
                    />
                    <Bar dataKey="late_delivery_pct" radius={[6, 6, 0, 0]}>
                      {comparisonData.tenants.map((entry, index) => (
                        <Cell
                          key={`cell-late-${index}`}
                          fill={
                            entry.late_delivery_pct >= 25
                              ? '#EF4444'
                              : entry.late_delivery_pct >= 10
                              ? '#F59E0B'
                              : '#10B981'
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Detailed Side-by-Side Comparison Metrics Table */}
          <div className="rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
            <div className="p-4 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
              <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
                <Layers className="w-4 h-4 text-helios-accent-blue" />
                <span>Side-by-Side Metrics Matrix</span>
              </h3>
              <span className="text-[11px] text-slate-400 font-mono">
                Compared at {formatDateTimeIN(comparisonData.compared_at)}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02] text-slate-400 uppercase font-semibold text-[11px] tracking-wider">
                    <th className="py-3 px-4">Metric</th>
                    {comparisonData.tenants.map((t) => {
                      const asOfStr = formatDateAsOf(t.data_as_of);
                      return (
                        <th key={t.tenant_id} className="py-3 px-4 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span>{t.tenant_name}</span>
                            {asOfStr ? (
                              <span className="text-[10px] font-normal text-slate-400 dark:text-slate-500 whitespace-nowrap">
                                (Data as of {asOfStr})
                              </span>
                            ) : (
                              <span className="text-[10px] font-normal text-slate-400 dark:text-slate-500 whitespace-nowrap">
                                (No data)
                              </span>
                            )}
                          </div>
                          <span className="block text-[10px] text-slate-400 font-normal uppercase mt-0.5">
                            Tier: {t.tier}
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Gross Revenue</td>
                    {comparisonData.tenants.map((t) => (
                      <td key={t.tenant_id} className="py-3 px-4 font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                        {formatINR(t.total_revenue ?? 0)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Total Order Volume</td>
                    {comparisonData.tenants.map((t) => (
                      <td key={t.tenant_id} className="py-3 px-4 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatCountIN(t.total_orders ?? 0)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Average Order Value (AOV)</td>
                    {comparisonData.tenants.map((t) => (
                      <td key={t.tenant_id} className="py-3 px-4 font-mono font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatINR(t.avg_order_value ?? 0)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Shipment Volume</td>
                    {comparisonData.tenants.map((t) => (
                      <td key={t.tenant_id} className="py-3 px-4 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatCountIN(t.total_shipments ?? 0)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Late Delivery Rate</td>
                    {comparisonData.tenants.map((t) => {
                      const latePct = t.late_delivery_pct ?? 0;
                      return (
                        <td key={t.tenant_id} className="py-3 px-4">
                          <span
                            className={`font-mono font-bold ${
                              latePct >= 25
                                ? 'text-rose-600 dark:text-rose-400'
                                : latePct >= 10
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-emerald-600 dark:text-emerald-400'
                            }`}
                          >
                            {latePct.toFixed(1)}%
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-semibold text-slate-500">Avg Shipping Transit Time</td>
                    {comparisonData.tenants.map((t) => (
                      <td key={t.tenant_id} className="py-3 px-4 font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {Number(t.avg_shipping_days ?? 0).toFixed(1)} days
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default TenantComparison;
