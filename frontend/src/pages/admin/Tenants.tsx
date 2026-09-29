import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  Plus,
  Search,
  RefreshCw,
  Power,
  XCircle,
  Lock,
  Eye,
} from 'lucide-react';
import { Tenant } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { useAuth } from '@/hooks/useAuth';

export const Tenants: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Form state
  const [name, setName] = useState<string>('');
  const [slug, setSlug] = useState<string>('');
  const [catalogName, setCatalogName] = useState<string>('helios_catalog');
  const [schemaName, setSchemaName] = useState<string>('');
  const [tier, setTier] = useState<'Starter' | 'Growth' | 'Enterprise'>('Growth');
  const [formError, setFormError] = useState<string | null>(null);

  const loadTenants = async () => {
    setIsLoading(true);
    try {
      const data = await adminService.getTenants();
      // If team_member, filter to assigned tenants if user has assigned_tenants
      if (!isAdmin && user) {
        const assigned = (user as any).assigned_tenants || ['1', '2'];
        setTenants(data.filter((t) => assigned.includes(t.tenant_id) || assigned.includes(t.slug)));
      } else {
        setTenants(data);
      }
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, [isAdmin, user]);

  const handleNameChange = (val: string) => {
    setName(val);
    const derivedSlug = val.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
    setSlug(derivedSlug);
    setSchemaName(derivedSlug);
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError('Organization name is required.');
      return;
    }
    setIsSubmitting(true);
    setFormError(null);

    try {
      const newTenant = await adminService.createTenant({
        name,
        slug: slug || name.toLowerCase().replace(/\s+/g, '_'),
        catalog_name: catalogName,
        schema_name: schemaName || slug,
        tier,
      });
      setTenants((prev) => [newTenant, ...prev]);
      setShowModal(false);
      setName('');
      setSlug('');
      setSchemaName('');
    } catch (err: any) {
      setFormError(err.message || 'Failed to create tenant.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleDeactivate = async (tenantId: string) => {
    if (!isAdmin) return; // Strict role check
    try {
      const res = await adminService.deactivateTenant(tenantId);
      setTenants((prev) =>
        prev.map((t) => (t.tenant_id === tenantId ? { ...t, is_active: res.is_active } : t))
      );
    } catch {
      // Handled
    }
  };

  const filteredTenants = tenants.filter((t) => {
    return (
      searchQuery === '' ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.catalog_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Tenant Directory & Unity Catalog Isolation
          </h1>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            {isAdmin
              ? 'Global registry of customer organizations, catalog schemas, and tenant lifecycle.'
              : 'Directory of your assigned customer tenant organizations and schemas.'}
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            type="button"
            onClick={loadTenants}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-helios-accent-blue' : ''}`} />
            <span>Refresh</span>
          </button>

          {/* Add New Tenant Button - Available to BOTH Team Member and Admin */}
          <button
            type="button"
            onClick={() => {
              setFormError(null);
              setShowModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Tenant</span>
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search tenants by name, slug, or catalog..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>
        <div className="text-xs text-slate-400">
          Showing <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{filteredTenants.length}</span> tenants
        </div>
      </div>

      {/* Tenants Table */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : filteredTenants.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-blue-500/10 text-helios-accent-blue flex items-center justify-center">
              <Building2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No Tenants Found
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              {isAdmin ? 'No customer tenant organizations registered yet.' : 'No tenants currently assigned to your account.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                  <th className="py-3 px-4 font-semibold">Organization</th>
                  <th className="py-3 px-4 font-semibold">Unity Catalog Namespace</th>
                  <th className="py-3 px-4 font-semibold">Tier</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Active Pipelines</th>
                  <th className="py-3 px-4 font-semibold text-right">Lifecycle Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {filteredTenants.map((tenant) => (
                  <tr key={tenant.tenant_id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                    <td className="py-3.5 px-4 font-medium">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center text-slate-500 shrink-0">
                          <Building2 className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-bold">{tenant.name}</div>
                          <div className="text-[11px] font-mono text-slate-400">
                            {tenant.slug}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-helios-accent-blue">
                      {tenant.catalog_name}.{tenant.schema_name}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-blue-500/10 text-helios-accent-blue border border-blue-500/20">
                        {tenant.tier}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      {tenant.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span>Active</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                          <span>Deactivated</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 font-mono">
                      {tenant.active_pipelines || 0} pipelines
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* View Dashboard action (Oversight View-As) */}
                        <Link
                          to={`/admin/oversight/dashboard/${tenant.tenant_id}`}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-helios-accent-blue/10 hover:bg-helios-accent-blue/20 text-helios-accent-blue border border-helios-accent-blue/20 transition-colors"
                          title="View-As tenant dashboard"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Dashboard</span>
                        </Link>

                        {/* Deactivate control: Enabled for Admin ONLY */}
                        {isAdmin ? (
                          <button
                            type="button"
                            onClick={() => handleToggleDeactivate(tenant.tenant_id)}
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                              tenant.is_active
                                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                                : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                            }`}
                            title={tenant.is_active ? 'Deactivate tenant' : 'Reactivate tenant'}
                          >
                            <Power className="w-3.5 h-3.5" />
                            <span>{tenant.is_active ? 'Deactivate' : 'Reactivate'}</span>
                          </button>
                        ) : (
                          <div
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-black/5 dark:bg-white/5 text-slate-400 cursor-not-allowed border border-helios-border-light dark:border-helios-border-dark opacity-60"
                            title="Admin role required to modify tenant lifecycle"
                          >
                            <Lock className="w-3 h-3" />
                            <span>Deactivate</span>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add New Tenant Modal (Both Admin and Team Member can access) */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-helios-accent-blue" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Onboard New Tenant Organization
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateTenant} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-400 mb-1">Organization Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Pacific Coast Gear"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-400 mb-1">Tenant Slug (Identifier)</label>
                <input
                  type="text"
                  placeholder="pacific_coast_gear"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  className="w-full px-3 py-2 font-mono rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Catalog Name</label>
                  <input
                    type="text"
                    value={catalogName}
                    onChange={(e) => setCatalogName(e.target.value)}
                    className="w-full px-3 py-2 font-mono rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Schema Name</label>
                  <input
                    type="text"
                    value={schemaName}
                    onChange={(e) => setSchemaName(e.target.value)}
                    className="w-full px-3 py-2 font-mono rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-400 mb-1">Service Tier</label>
                <select
                  value={tier}
                  onChange={(e) => setTier(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                >
                  <option value="Starter">Starter (Shared Compute)</option>
                  <option value="Growth">Growth (Dedicated Lakehouse)</option>
                  <option value="Enterprise">Enterprise (High-Concurrency Cluster)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Provisioning...' : 'Provision Tenant'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tenants;
