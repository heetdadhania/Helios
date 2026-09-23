import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Users,
  UserPlus,
  ShieldCheck,
  Search,
  Building2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Edit2,
} from 'lucide-react';
import { TeamMember, Tenant } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { useAuth } from '@/hooks/useAuth';

export const TeamMembers: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();

  // CODING RULE: Role-gate TeamMembers.tsx to admin only (redirect team_member away)
  if (!authLoading && user?.role !== 'admin') {
    return <Navigate to="/admin/uploads" replace />;
  }

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showAssignModal, setShowAssignModal] = useState<boolean>(false);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);

  // New member form
  const [newName, setNewName] = useState<string>('');
  const [newEmail, setNewEmail] = useState<string>('');
  const [newRole, setNewRole] = useState<'admin' | 'team_member'>('team_member');
  const [selectedTenants, setSelectedTenants] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [membersData, tenantsData] = await Promise.all([
        adminService.getTeamMembers(),
        adminService.getTenants(),
      ]);
      setTeamMembers(membersData);
      setTenants(tenantsData);
    } catch {
      // Fallback in adminService
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      loadData();
    }
  }, [user]);

  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newEmail.trim()) {
      setFormError('Name and email are required.');
      return;
    }
    setIsSubmitting(true);
    setFormError(null);

    try {
      const created = await adminService.createTeamMember({
        name: newName,
        email: newEmail,
        role: newRole,
        assigned_tenants: selectedTenants,
      });
      setTeamMembers((prev) => [created, ...prev]);
      setShowAddModal(false);
      setNewName('');
      setNewEmail('');
      setSelectedTenants([]);
    } catch (err: any) {
      setFormError(err.message || 'Failed to create team member.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignTenant = async (tenantId: string) => {
    if (!selectedMember) return;
    try {
      await adminService.assignTenant({
        user_id: selectedMember.user_id,
        tenant_id: tenantId,
      });
      setTeamMembers((prev) =>
        prev.map((m) => {
          if (m.user_id === selectedMember.user_id) {
            const current = m.assigned_tenants || [];
            const updated = current.includes(tenantId)
              ? current.filter((id) => id !== tenantId)
              : [...current, tenantId];
            return { ...m, assigned_tenants: updated };
          }
          return m;
        })
      );
      setSelectedMember((prev) => {
        if (!prev) return null;
        const current = prev.assigned_tenants || [];
        const updated = current.includes(tenantId)
          ? current.filter((id) => id !== tenantId)
          : [...current, tenantId];
        return { ...prev, assigned_tenants: updated };
      });
    } catch {
      // Handled
    }
  };

  const getTenantName = (idOrSlug: string) => {
    const t = tenants.find((item) => item.tenant_id === idOrSlug || item.slug === idOrSlug);
    return t ? t.name : `Tenant #${idOrSlug}`;
  };

  const filteredMembers = teamMembers.filter((m) => {
    return (
      searchQuery === '' ||
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Helios Operations Team & Roles
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              Admin Exclusive
            </span>
          </div>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Manage platform team accounts, grant administrative access, and assign specific tenant organizations to team members.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            type="button"
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-helios-accent-blue' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setFormError(null);
              setShowAddModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Team Member</span>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search team by name, email, or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>
        <div className="text-xs text-slate-400">
          Total: <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{filteredMembers.length}</span> staff
        </div>
      </div>

      {/* Team Table */}
      <div className="rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No Team Members Found
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              Add operations team accounts to delegate data ingestion review and pipeline monitoring.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-slate-400 bg-black/[0.02] dark:bg-white/[0.02]">
                  <th className="py-3 px-4 font-semibold">User</th>
                  <th className="py-3 px-4 font-semibold">Role</th>
                  <th className="py-3 px-4 font-semibold">Assigned Tenants Scope</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {filteredMembers.map((member) => (
                  <tr key={member.user_id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-helios-accent-blue to-helios-accent-teal text-white flex items-center justify-center font-bold text-xs">
                          {member.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold">{member.name}</div>
                          <div className="text-[11px] text-slate-400">{member.email}</div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      {member.role === 'admin' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                          <ShieldCheck className="w-3 h-3" />
                          <span>Admin</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                          <span>Team Member</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      {member.role === 'admin' ? (
                        <span className="text-[11px] font-semibold text-helios-accent-teal">
                          All Tenants (Unrestricted Access)
                        </span>
                      ) : member.assigned_tenants && member.assigned_tenants.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5 max-w-xs">
                          {member.assigned_tenants.map((tId) => (
                            <span
                              key={tId}
                              className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-slate-300"
                            >
                              {getTenantName(tId)}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[11px] text-rose-500 font-medium">
                          No Tenants Assigned
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span>Active</span>
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      {member.role === 'team_member' && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedMember(member);
                            setShowAssignModal(true);
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                        >
                          <Edit2 className="w-3 h-3 text-helios-accent-blue" />
                          <span>Assign Tenants</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Team Member Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-helios-accent-blue" />
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Add Operations Team Member
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
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

            <form onSubmit={handleCreateMember} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-400 mb-1">Full Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Alex Morgan"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-400 mb-1">Corporate Email *</label>
                <input
                  type="email"
                  placeholder="alex@helios.io"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-400 mb-1">Platform Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                >
                  <option value="team_member">Team Member (Scoped to assigned tenants)</option>
                  <option value="admin">Admin (Full tenant & user management)</option>
                </select>
              </div>

              {newRole === 'team_member' && (
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Assign Initial Tenants</label>
                  <div className="space-y-1 max-h-36 overflow-y-auto p-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark">
                    {tenants.map((t) => {
                      const isChecked = selectedTenants.includes(t.tenant_id);
                      return (
                        <label key={t.tenant_id} className="flex items-center gap-2 cursor-pointer p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {
                              setSelectedTenants((prev) =>
                                isChecked
                                  ? prev.filter((id) => id !== t.tenant_id)
                                  : [...prev, t.tenant_id]
                              );
                            }}
                            className="rounded text-helios-accent-blue focus:ring-0"
                          />
                          <span>{t.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Tenants Modal */}
      {showAssignModal && selectedMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Assign Tenants to {selectedMember.name}
                </h3>
                <p className="text-[11px] text-slate-400">{selectedMember.email}</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowAssignModal(false);
                  setSelectedMember(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Check organizations that this team member is authorized to review pending uploads, pipeline runs, and quality logs for.
            </p>

            <div className="space-y-1.5 max-h-56 overflow-y-auto text-xs">
              {tenants.map((t) => {
                const isAssigned = (selectedMember.assigned_tenants || []).includes(t.tenant_id);
                return (
                  <div
                    key={t.tenant_id}
                    onClick={() => handleAssignTenant(t.tenant_id)}
                    className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-colors ${
                      isAssigned
                        ? 'bg-helios-accent-blue/10 border-helios-accent-blue text-helios-text-primary-light dark:text-helios-text-primary-dark'
                        : 'bg-black/5 dark:bg-white/5 border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4" />
                      <div>
                        <div className="font-semibold text-xs">{t.name}</div>
                        <div className="text-[10px] font-mono text-slate-400">{t.catalog_name}.{t.schema_name}</div>
                      </div>
                    </div>
                    {isAssigned ? (
                      <CheckCircle2 className="w-4 h-4 text-helios-accent-blue shrink-0" />
                    ) : (
                      <span className="text-[10px] font-semibold text-slate-500">Assign</span>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-2 border-t border-helios-border-light dark:border-helios-border-dark">
              <button
                type="button"
                onClick={() => {
                  setShowAssignModal(false);
                  setSelectedMember(null);
                }}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamMembers;
