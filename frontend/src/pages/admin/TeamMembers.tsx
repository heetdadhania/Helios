import React, { useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
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
  Copy,
  Check,
  AlertCircle,
  UserCheck,
  UserX,
  Briefcase,
  User,
  Shield,
} from 'lucide-react';
import { CreateTeamMemberResponse, TeamMember, Tenant } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { useAuth } from '@/hooks/useAuth';

const PHONE_REGEX = /^[0-9+\-() ]{7,20}$/;

const teamMemberSchema = z.object({
  // Personal
  name: z.string().min(2, 'Full Name must be at least 2 characters').max(150),
  email: z.string().email('Please enter a valid corporate email'),
  phone_number: z
    .string()
    .min(7, 'Phone number must be at least 7 characters')
    .max(20, 'Phone number must be at most 20 characters')
    .regex(PHONE_REGEX, 'Phone must contain only digits, spaces, plus, dash, and parentheses'),
  // Account
  role: z.enum(['team_member', 'admin']),
  // Work
  staff_id: z.string().max(100).optional().or(z.literal('')),
  designation: z.string().max(150).optional().or(z.literal('')),
  // Assignment
  tenant_ids: z.array(z.number()).optional().default([]),
});

type TeamMemberFormValues = z.infer<typeof teamMemberSchema>;

export const TeamMembers: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();

  // Role-gate TeamMembers.tsx to admin only
  if (!authLoading && user?.role !== 'admin') {
    return <Navigate to="/admin/uploads" replace />;
  }

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Add Member Modal & Result Dialog
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [createdMemberResult, setCreatedMemberResult] = useState<CreateTeamMemberResponse | null>(null);
  const [hasCopiedPassword, setHasCopiedPassword] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Edit Assignments Modal
  const [showEditAssignmentsModal, setShowEditAssignmentsModal] = useState<boolean>(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);
  const [selectedTenantIdsForEdit, setSelectedTenantIdsForEdit] = useState<number[]>([]);
  const [isSavingAssignments, setIsSavingAssignments] = useState<boolean>(false);

  // Status Toggle Confirmation / In-flight
  const [togglingUserId, setTogglingUserId] = useState<string | number | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm<TeamMemberFormValues>({
    resolver: zodResolver(teamMemberSchema),
    defaultValues: {
      name: '',
      email: '',
      phone_number: '',
      role: 'team_member',
      staff_id: '',
      designation: '',
      tenant_ids: [],
    },
  });

  const selectedTenantIds = watch('tenant_ids') || [];
  const selectedRole = watch('role');

  const loadData = async () => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const [membersData, tenantsData] = await Promise.all([
        adminService.getTeamMembers(),
        adminService.getTenants(),
      ]);
      setTeamMembers(membersData);
      setTenants(tenantsData);
    } catch (err: any) {
      setGeneralError(err?.response?.data?.detail || err.message || 'Failed to load team members.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      loadData();
    }
  }, [user]);

  const handleOpenAddModal = () => {
    reset({
      name: '',
      email: '',
      phone_number: '',
      role: 'team_member',
      staff_id: '',
      designation: '',
      tenant_ids: [],
    });
    clearErrors();
    setGeneralError(null);
    setShowAddModal(true);
  };

  const handleCloseAddModal = () => {
    setShowAddModal(false);
    clearErrors();
    setGeneralError(null);
  };

  const onSubmitAddMember = async (values: TeamMemberFormValues) => {
    setGeneralError(null);
    clearErrors('email');
    try {
      const res = await adminService.createTeamMember({
        name: values.name.trim(),
        email: values.email.trim().toLowerCase(),
        phone_number: values.phone_number.trim(),
        role: values.role,
        staff_id: values.staff_id?.trim() || undefined,
        designation: values.designation?.trim() || undefined,
        tenant_ids: values.tenant_ids,
        assigned_tenants: values.tenant_ids?.map(String),
      });

      setTeamMembers((prev) => [res, ...prev]);
      setShowAddModal(false);
      setCreatedMemberResult(res);
      setHasCopiedPassword(false);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 409 || (typeof detail === 'string' && detail.toLowerCase().includes('already exists'))) {
        setError('email', {
          type: 'manual',
          message: detail || `A user with email '${values.email.trim()}' already exists.`,
        });
      } else {
        setGeneralError(detail || err.message || 'Failed to create team member.');
      }
    }
  };

  const handleCopyPassword = () => {
    if (createdMemberResult?.temporary_password) {
      navigator.clipboard.writeText(createdMemberResult.temporary_password);
      setHasCopiedPassword(true);
      setTimeout(() => setHasCopiedPassword(false), 2500);
    }
  };

  const handleDismissSuccessDialog = () => {
    setCreatedMemberResult(null);
    setHasCopiedPassword(false);
  };

  // Open Edit Assignments Modal
  const handleOpenEditAssignments = (member: TeamMember) => {
    setEditingMember(member);
    const initialIds: number[] = (member.tenant_ids || member.assigned_tenants || [])
      .map((id) => Number(id))
      .filter((n) => !isNaN(n));
    setSelectedTenantIdsForEdit(initialIds);
    setShowEditAssignmentsModal(true);
  };

  const handleSaveAssignments = async () => {
    if (!editingMember) return;
    setIsSavingAssignments(true);
    try {
      await adminService.replaceAssignments(
        editingMember.user_id,
        selectedTenantIdsForEdit
      );
      setTeamMembers((prev) =>
        prev.map((m) =>
          String(m.user_id) === String(editingMember.user_id)
            ? {
                ...m,
                assigned_tenants: selectedTenantIdsForEdit.map(String),
                tenant_ids: selectedTenantIdsForEdit,
              }
            : m
        )
      );
      setShowEditAssignmentsModal(false);
      setEditingMember(null);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update assignments.');
    } finally {
      setIsSavingAssignments(false);
    }
  };

  // Activate / Deactivate Toggle
  const handleToggleActive = async (member: TeamMember) => {
    const newStatus = !member.is_active;
    const actionLabel = newStatus ? 'activate' : 'deactivate';
    if (!window.confirm(`Are you sure you want to ${actionLabel} ${member.name}?`)) {
      return;
    }
    setTogglingUserId(member.user_id);
    try {
      await adminService.toggleTeamMemberActive(member.user_id, newStatus);
      setTeamMembers((prev) =>
        prev.map((m) =>
          String(m.user_id) === String(member.user_id) ? { ...m, is_active: newStatus } : m
        )
      );
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to ${actionLabel} account.`);
    } finally {
      setTogglingUserId(null);
    }
  };

  const getTenantName = (idOrSlug: string | number) => {
    const t = tenants.find(
      (item) => String(item.tenant_id) === String(idOrSlug) || item.slug === String(idOrSlug)
    );
    return t ? t.business_name || t.name : `Organization #${idOrSlug}`;
  };

  const filteredMembers = useMemo(() => {
    return teamMembers.filter((m) => {
      const query = searchQuery.toLowerCase();
      return (
        query === '' ||
        m.name.toLowerCase().includes(query) ||
        m.email.toLowerCase().includes(query) ||
        (m.phone_number && m.phone_number.toLowerCase().includes(query)) ||
        (m.staff_id && m.staff_id.toLowerCase().includes(query)) ||
        (m.designation && m.designation.toLowerCase().includes(query)) ||
        m.role.toLowerCase().includes(query)
      );
    });
  }, [teamMembers, searchQuery]);

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
            Register team accounts, generate temporary credentials, and configure organization assignments.
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

          {/* Add Team Member Button */}
          <button
            type="button"
            onClick={handleOpenAddModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Team Member</span>
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, email, phone, badge, or role..."
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
            <div className="h-10 w-full bg-slate-100 dark:bg-slate-900 rounded" />
          </div>
        ) : generalError ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Failed to Load Team Members
            </h3>
            <p className="text-xs text-rose-600 dark:text-rose-400 max-w-sm mx-auto">
              {generalError}
            </p>
            <button
              type="button"
              onClick={loadData}
              className="px-4 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors"
            >
              Retry
            </button>
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
                  <th className="py-3 px-4 font-semibold">User Details</th>
                  <th className="py-3 px-4 font-semibold">Role & Title</th>
                  <th className="py-3 px-4 font-semibold">Assigned Organizations Scope</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {filteredMembers.map((member) => {
                  const assignedList = member.tenant_ids || member.assigned_tenants || [];
                  const isTogglingThis = String(togglingUserId) === String(member.user_id);

                  return (
                    <tr key={member.user_id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                      {/* User Info */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-helios-accent-blue to-helios-accent-teal text-white flex items-center justify-center font-bold text-xs shrink-0">
                            {member.name.substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold flex items-center gap-1.5">
                              <span>{member.name}</span>
                              {member.staff_id && (
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-black/5 dark:bg-white/5 text-slate-400 border border-helios-border-light dark:border-helios-border-dark">
                                  {member.staff_id}
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                              <span>{member.email}</span>
                              {member.phone_number && (
                                <>
                                  <span>•</span>
                                  <span>{member.phone_number}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Role & Title */}
                      <td className="py-3.5 px-4">
                        <div>
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
                          {member.designation && (
                            <div className="text-[11px] text-slate-400 mt-1 font-medium">
                              {member.designation}
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Assigned Organizations */}
                      <td className="py-3.5 px-4">
                        {member.role === 'admin' ? (
                          <span className="text-[11px] font-semibold text-helios-accent-teal">
                            All Organizations (Unrestricted Access)
                          </span>
                        ) : assignedList.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 max-w-xs">
                            {assignedList.map((tId) => (
                              <span
                                key={String(tId)}
                                className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-slate-300"
                              >
                                {getTenantName(tId)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-[11px] text-rose-500 font-medium">
                            No Organizations Assigned
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        {member.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <span>Active</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                            <span>Deactivated</span>
                          </span>
                        )}
                      </td>

                      {/* Row Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Edit Assignments Action */}
                          {member.role === 'team_member' && (
                            <button
                              type="button"
                              onClick={() => handleOpenEditAssignments(member)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                              title="Edit Assigned Organizations"
                            >
                              <Edit2 className="w-3 h-3 text-helios-accent-blue" />
                              <span>Assignments</span>
                            </button>
                          )}

                          {/* Activate / Deactivate Action */}
                          <button
                            type="button"
                            onClick={() => handleToggleActive(member)}
                            disabled={isTogglingThis}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors disabled:opacity-50 ${
                              member.is_active
                                ? 'border-rose-500/30 text-rose-500 hover:bg-rose-500/10'
                                : 'border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10'
                            }`}
                            title={member.is_active ? 'Deactivate Account' : 'Activate Account'}
                          >
                            {isTogglingThis ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : member.is_active ? (
                              <>
                                <UserX className="w-3 h-3" />
                                <span>Deactivate</span>
                              </>
                            ) : (
                              <>
                                <UserCheck className="w-3 h-3" />
                                <span>Activate</span>
                              </>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* MODAL 1: Add Team Member (Four Labeled Sections)                          */}
      {/* ========================================================================= */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-5">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-helios-accent-blue/15 flex items-center justify-center text-helios-accent-blue">
                  <UserPlus className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Register New Team Member
                  </h3>
                  <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Server will generate a high-entropy temporary password.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseAddModal}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* General / Server Error */}
            {generalError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{generalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmitAddMember)} className="space-y-5 text-xs">
              
              {/* SECTION 1: Personal (Full Name, Email, Phone) */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <User className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>1. Personal Information</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-slate-400 mb-1">
                      Full Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Sarah Connor"
                      {...register('name')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.name ? 'border-rose-500 focus:ring-rose-500' : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.name && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.name.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-400 mb-1">
                      Corporate Email <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="email"
                      placeholder="e.g. sarah@helios.io"
                      {...register('email')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.email ? 'border-rose-500 focus:ring-rose-500' : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.email && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.email.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-400 mb-1">
                      Phone Number <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. +1 (555) 234-5678"
                      {...register('phone_number')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.phone_number ? 'border-rose-500 focus:ring-rose-500' : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.phone_number && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.phone_number.message}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* SECTION 2: Account (Role dropdown: Team Member or Admin) */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <Shield className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>2. Account & Permissions</span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-400 mb-1">
                    Platform Role <span className="text-rose-500">*</span>
                  </label>
                  <select
                    {...register('role')}
                    className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                  >
                    <option value="team_member">Team Member (Scoped to assigned organizations)</option>
                    <option value="admin">Admin (Full administrative & organization access)</option>
                  </select>
                  {errors.role && (
                    <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.role.message}</p>
                  )}
                </div>
              </div>

              {/* SECTION 3: Work (Staff ID optional, Designation optional) */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>3. Work Profile (Optional)</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-400 mb-1">
                      Staff ID / Employee Badge
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. EMP-1049"
                      {...register('staff_id')}
                      className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-400 mb-1">
                      Designation / Job Title
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Lead Pipeline Engineer"
                      {...register('designation')}
                      className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 4: Assignment (multi-select of tenants, optional) */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <Building2 className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>4. Organization Scope Assignments</span>
                </div>

                {selectedRole === 'admin' ? (
                  <p className="text-[11px] text-helios-accent-teal italic">
                    Administrators possess automatic platform-wide visibility across all customer organizations.
                  </p>
                ) : (
                  <div>
                    <label className="block font-semibold text-slate-400 mb-1.5">
                      Select Organizations <span className="font-normal text-slate-500">(Optional)</span>
                    </label>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark">
                      {tenants.map((t) => {
                        const tidNum = Number(t.tenant_id);
                        const isChecked = selectedTenantIds.includes(tidNum);

                        return (
                          <label
                            key={t.tenant_id}
                            className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                              isChecked
                                ? 'bg-helios-accent-blue/15 border border-helios-accent-blue/30 text-helios-text-primary-light dark:text-helios-text-primary-dark'
                                : 'hover:bg-black/5 dark:hover:bg-white/5 text-slate-400'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => {
                                  if (isChecked) {
                                    setValue(
                                      'tenant_ids',
                                      selectedTenantIds.filter((id) => id !== tidNum)
                                    );
                                  } else {
                                    setValue('tenant_ids', [...selectedTenantIds, tidNum]);
                                  }
                                }}
                                className="rounded text-helios-accent-blue focus:ring-0"
                              />
                              <span className="font-semibold text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark">
                                {t.business_name || t.name}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-400">
                              #{t.tenant_id}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Form Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={handleCloseAddModal}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-all disabled:opacity-50 shadow-sm"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Creating Member...</span>
                    </>
                  ) : (
                    <span>Register Team Member</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: Temporary Password Display Dialog (Shown ONCE on Success)        */}
      {/* ========================================================================= */}
      {createdMemberResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Team Member Registered Successfully
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Temporary credentials generated for first login.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark space-y-2 text-xs">
              <div className="flex justify-between items-center text-slate-400">
                <span>Member:</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {createdMemberResult.name} ({createdMemberResult.role})
                </span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Login Email:</span>
                <span className="font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {createdMemberResult.email}
                </span>
              </div>
            </div>

            {/* Temporary Password Field with Copy Button */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Temporary Password
              </label>
              <div className="flex items-center gap-2">
                <div className="flex-1 px-3 py-2.5 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark font-mono text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark select-all">
                  {createdMemberResult.temporary_password || '********'}
                </div>
                <button
                  type="button"
                  onClick={handleCopyPassword}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white transition-all shadow-sm flex-shrink-0"
                >
                  {hasCopiedPassword ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Warning Note: Will not be shown again */}
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-500 text-xs flex items-start gap-2 leading-relaxed">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Important:</strong> This temporary password will <strong>not</strong> be shown again.
                Please copy and deliver it securely to the team member.
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleDismissSuccessDialog}
                className="w-full py-2.5 text-xs font-bold rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: Edit Tenant Assignments for Existing Team Member                 */}
      {/* ========================================================================= */}
      {showEditAssignmentsModal && editingMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Edit Organization Assignments
                </h3>
                <p className="text-xs text-slate-400">
                  {editingMember.name} ({editingMember.email})
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowEditAssignmentsModal(false);
                  setEditingMember(null);
                }}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Select or clear authorized customer organizations for this team member:
            </p>

            <div className="space-y-1.5 max-h-60 overflow-y-auto text-xs">
              {tenants.map((t) => {
                const tidNum = Number(t.tenant_id);
                const isAssigned = selectedTenantIdsForEdit.includes(tidNum);

                return (
                  <div
                    key={t.tenant_id}
                    onClick={() => {
                      setSelectedTenantIdsForEdit((prev) =>
                        isAssigned ? prev.filter((id) => id !== tidNum) : [...prev, tidNum]
                      );
                    }}
                    className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-colors ${
                      isAssigned
                        ? 'bg-helios-accent-blue/10 border-helios-accent-blue text-helios-text-primary-light dark:text-helios-text-primary-dark'
                        : 'bg-black/5 dark:bg-white/5 border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Building2 className="w-4 h-4 text-helios-accent-blue" />
                      <div>
                        <div className="font-semibold text-xs">
                          {t.business_name || t.name}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">
                          {t.catalog_name}.{t.schema_name}
                        </div>
                      </div>
                    </div>
                    {isAssigned ? (
                      <CheckCircle2 className="w-4 h-4 text-helios-accent-blue shrink-0" />
                    ) : (
                      <span className="text-[10px] font-semibold text-slate-500">Unassigned</span>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-helios-border-light dark:border-helios-border-dark">
              <button
                type="button"
                onClick={() => {
                  setShowEditAssignmentsModal(false);
                  setEditingMember(null);
                }}
                disabled={isSavingAssignments}
                className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveAssignments}
                disabled={isSavingAssignments}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors disabled:opacity-50"
              >
                {isSavingAssignments ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Save Assignments</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamMembers;
