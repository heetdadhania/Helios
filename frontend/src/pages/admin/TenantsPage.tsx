import React, { useState } from 'react';
import { Plus, Building2 } from 'lucide-react';
import { TenantAccount } from '@/types/data';

const initialTenants: TenantAccount[] = [
  {
    id: 'ten_1',
    name: 'Acme Retail Group',
    slug: 'acme_retail',
    catalogName: 'helios_catalog.acme_retail',
    tier: 'Enterprise',
    activePipelines: 8,
    status: 'active',
    createdAt: 'Aug 12, 2026',
  },
  {
    id: 'ten_2',
    name: 'Nordic Outfitters',
    slug: 'nordic_outfitters',
    catalogName: 'helios_catalog.nordic_outfitters',
    tier: 'Growth',
    activePipelines: 4,
    status: 'active',
    createdAt: 'Aug 29, 2026',
  },
  {
    id: 'ten_3',
    name: 'Apex Direct Co.',
    slug: 'apex_direct',
    catalogName: 'helios_catalog.apex_direct',
    tier: 'Starter',
    activePipelines: 2,
    status: 'active',
    createdAt: 'Sep 10, 2026',
  },
];

export const TenantsPage: React.FC = () => {
  const [tenants, setTenants] = useState<TenantAccount[]>(initialTenants);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [newOrgName, setNewOrgName] = useState<string>('');

  const handleCreateTenant = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName) return;
    const slug = newOrgName.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const newTenant: TenantAccount = {
      id: 'ten_' + Date.now(),
      name: newOrgName,
      slug,
      catalogName: `helios_catalog.${slug}`,
      tier: 'Growth',
      activePipelines: 1,
      status: 'active',
      createdAt: 'Today',
    };
    setTenants((prev) => [newTenant, ...prev]);
    setNewOrgName('');
    setShowModal(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Tenant Directory & Catalog Routing
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Provision isolated namespaces in Databricks Unity Catalog for customer organizations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="px-3.5 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors flex items-center gap-1.5 shadow-sm self-start"
        >
          <Plus className="w-4 h-4" />
          <span>Onboard New Tenant</span>
        </button>
      </div>

      {showModal && (
        <div className="p-5 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-accent-blue space-y-3">
          <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Provision Organization
          </h3>
          <form onSubmit={handleCreateTenant} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Organization Name (e.g. Zenith Brands)"
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              className="flex-1 px-3 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-teal text-white hover:bg-emerald-600"
              >
                Provision
              </button>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-3 py-2 text-xs font-semibold rounded-control border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">Organization</th>
                <th className="pb-3 font-semibold">Unity Catalog Namespace</th>
                <th className="pb-3 font-semibold">Tier</th>
                <th className="pb-3 font-semibold">Pipelines</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {tenants.map((ten) => (
                <tr key={ten.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3.5">
                    <div className="flex items-center gap-2.5">
                      <Building2 className="w-4 h-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <div>
                        <div className="font-semibold">{ten.name}</div>
                        <div className="text-[11px] font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          {ten.slug}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 font-mono text-helios-accent-blue">{ten.catalogName}</td>
                  <td className="py-3.5">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-blue-500/10 text-helios-accent-blue">
                      {ten.tier}
                    </span>
                  </td>
                  <td className="py-3.5">{ten.activePipelines} active</td>
                  <td className="py-3.5">
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-helios-accent-teal">
                      {ten.status}
                    </span>
                  </td>
                  <td className="py-3.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    {ten.createdAt}
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
