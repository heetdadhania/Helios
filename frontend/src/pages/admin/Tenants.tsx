import React, { useEffect, useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Building2,
  Plus,
  Search,
  RefreshCw,
  Power,
  XCircle,
  Lock,
  Copy,
  Check,
  User,
  MapPin,
  UserCheck,
  AlertCircle,
  Globe,
  Mail,
  Phone,
  Edit2,
  Key,
  UserX,
  UserPlus,
  AlertTriangle,
} from 'lucide-react';
import { Tenant, TeamMember } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/Toast';
import { Pagination } from '@/components/ui/Pagination';
import { formatDateIN } from '@/utils/currency';
import { useOrganizations } from '@/hooks/useOrganizations';

const INDUSTRY_OPTIONS = [
  'Apparel & Fashion',
  'Consumer Electronics',
  'Health, Beauty & Personal Care',
  'Home & Living',
  'Food & Beverage',
  'Sports & Outdoors',
  'Automotive & Industrial',
  'Retail & E-commerce',
  'Other',
];

export const INDIAN_STATES_AND_UTS = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
  'Andaman and Nicobar Islands',
  'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Jammu and Kashmir',
  'Ladakh',
  'Lakshadweep',
  'Puducherry',
] as const;

// Zod validation matching backend rules
const tenantFormSchema = z.object({
  // Business Section
  business_name: z
    .string()
    .min(2, 'Business name must be at least 2 characters')
    .max(150, 'Business name cannot exceed 150 characters'),
  industry: z
    .string()
    .min(1, 'Please select an industry vertical'),
  website_url: z
    .string()
    .optional()
    .refine(
      (val) => !val || val.trim() === '' || /^https?:\/\/.+/i.test(val.trim()),
      'Website URL must start with http:// or https://'
    ),
  tax_id: z
    .string()
    .optional()
    .refine(
      (val) => !val || val.trim() === '' || /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(val.trim().toUpperCase()),
      'Invalid GSTIN format (15 characters: e.g. 29ABCDE1234F1Z5)'
    ),

  // Contact Section
  contact_person_name: z
    .string()
    .min(2, 'Contact person name is required')
    .max(150, 'Contact person name cannot exceed 150 characters'),
  contact_email: z
    .string()
    .min(1, 'Contact email is required')
    .email('Please enter a valid email address'),
  phone_number: z
    .string()
    .min(10, 'Phone number must be at least 10 digits')
    .max(20, 'Phone number cannot exceed 20 characters')
    .regex(
      /^(\+91[\-\s]?)?[6-9]\d{9}$/,
      'Phone number must be a valid Indian number (10 digits starting with 6, 7, 8 or 9, optional +91)'
    ),
  owner_email: z
    .string()
    .min(1, 'Owner login email is required')
    .email('Please enter a valid owner login email address'),

  // Address Section
  address_line1: z
    .string()
    .min(2, 'Address Line 1 is required')
    .max(255, 'Address Line 1 cannot exceed 255 characters'),
  address_line2: z.string().optional(),
  city: z.string().min(1, 'City is required').max(100),
  state: z
    .string()
    .min(1, 'Please select a State / Union Territory')
    .refine((val) => (INDIAN_STATES_AND_UTS as readonly string[]).includes(val), 'Please select a valid Indian State or UT'),
  postal_code: z
    .string()
    .regex(/^[1-9][0-9]{5}$/, 'PIN code must be exactly 6 digits and cannot start with 0'),
  country: z.string().default('India'),

  // Assignment Section (Admin only)
  assigned_team_member_id: z.string().optional(),
});

type TenantFormValues = z.infer<typeof tenantFormSchema>;

export const Tenants: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const toast = useToast();

  const {
    organizations: tenants,
    isLoading,
    error: orgsError,
    refetch: loadTenants,
  } = useOrganizations();

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Unified temporary password dialog state
  const [tempPasswordModal, setTempPasswordModal] = useState<{
    title: string;
    subtitle: string;
    organization: string;
    email: string;
    password: string;
  } | null>(null);
  const [hasCopiedPassword, setHasCopiedPassword] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Edit Owner Dialog State
  const [editOwnerTenant, setEditOwnerTenant] = useState<Tenant | null>(null);
  const [editOwnerForm, setEditOwnerForm] = useState({ name: '', email: '', phone_number: '' });
  const [editOwnerErrors, setEditOwnerErrors] = useState<Record<string, string>>({});
  const [isSubmittingEdit, setIsSubmittingEdit] = useState<boolean>(false);

  // Reset Password Dialog State
  const [resetOwnerTenant, setResetOwnerTenant] = useState<Tenant | null>(null);
  const [isSubmittingReset, setIsSubmittingReset] = useState<boolean>(false);

  // Deactivate Owner Dialog State
  const [deactivateOwnerTenant, setDeactivateOwnerTenant] = useState<Tenant | null>(null);
  const [isSubmittingDeactivate, setIsSubmittingDeactivate] = useState<boolean>(false);

  // Replace Owner Dialog State
  const [replaceOwnerTenant, setReplaceOwnerTenant] = useState<Tenant | null>(null);
  const [replaceOwnerForm, setReplaceOwnerForm] = useState({ name: '', email: '', phone_number: '' });
  const [replaceOwnerErrors, setReplaceOwnerErrors] = useState<Record<string, string>>({});
  const [isSubmittingReplace, setIsSubmittingReplace] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: {
      business_name: '',
      industry: '',
      website_url: '',
      tax_id: '',
      contact_person_name: '',
      contact_email: '',
      phone_number: '',
      owner_email: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      postal_code: '',
      country: 'India',
      assigned_team_member_id: '',
    },
  });

  const contactEmailValue = watch('contact_email');
  const ownerEmailValue = watch('owner_email');

  // Combined error state
  const displayError = generalError || orgsError;

  // Load team members for Admin assignment dropdown
  useEffect(() => {
    if (isAdmin) {
      adminService
        .getTeamMembers()
        .then((members) => {
          setTeamMembers(members.filter((m) => m.role === 'team_member' && m.is_active));
        })
        .catch(() => {
          setTeamMembers([]);
        });
    }
  }, [isAdmin]);



  // Handle contact email blur/change to default owner_email if untouched
  const handleContactEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setValue('contact_email', val, { shouldValidate: true });
    if (!ownerEmailValue || ownerEmailValue === contactEmailValue) {
      setValue('owner_email', val, { shouldValidate: true });
    }
  };

  const handleOpenModal = () => {
    reset({
      business_name: '',
      industry: '',
      website_url: '',
      tax_id: '',
      contact_person_name: '',
      contact_email: '',
      phone_number: '',
      owner_email: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      postal_code: '',
      country: 'India',
      assigned_team_member_id: '',
    });
    setGeneralError(null);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    reset({
      business_name: '',
      industry: '',
      website_url: '',
      tax_id: '',
      contact_person_name: '',
      contact_email: '',
      phone_number: '',
      owner_email: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      postal_code: '',
      country: 'India',
      assigned_team_member_id: '',
    });
    setGeneralError(null);
  };

  const onSubmit = async (data: TenantFormValues) => {
    setGeneralError(null);
    try {
      const assignedIdNum = data.assigned_team_member_id
        ? parseInt(data.assigned_team_member_id, 10)
        : null;

      const newTenant = await adminService.createTenant({
        business_name: data.business_name.trim(),
        name: data.business_name.trim(),
        industry: data.industry,
        website_url: data.website_url?.trim() || null,
        tax_id: data.tax_id?.trim() || null,
        contact_person_name: data.contact_person_name.trim(),
        contact_email: data.contact_email.trim().toLowerCase(),
        phone_number: data.phone_number.trim(),
        owner_email: (data.owner_email || data.contact_email).trim().toLowerCase(),
        address_line1: data.address_line1.trim(),
        address_line2: data.address_line2?.trim() || null,
        city: data.city.trim(),
        state: data.state.trim(),
        postal_code: data.postal_code.trim(),
        country: 'India',
        assigned_team_member_id: assignedIdNum,
      });

      // Close onboarding modal and show temporary password dialog
      setShowModal(false);
      setHasCopiedPassword(false);
      setTempPasswordModal({
        title: 'Organization Onboarded Successfully',
        subtitle: 'Organization Owner credentials have been generated.',
        organization: data.business_name,
        email: newTenant.owner_email || data.owner_email || data.contact_email,
        password: newTenant.temporary_password || '',
      });
      toast.success(
        `Organization "${data.business_name}" onboarded successfully.`,
        'Organization Provisioned'
      );
      // Refresh list
      loadTenants();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || err?.message || '';

      if (status === 409) {
        const detailLower = detail.toLowerCase();
        if (detailLower.includes('business') || detailLower.includes('tenant') || detailLower.includes('organization')) {
          setError('business_name', {
            type: 'manual',
            message: detail || 'An active organization with this business name already exists.',
          });
        } else if (detailLower.includes('email') || detailLower.includes('user')) {
          setError('owner_email', {
            type: 'manual',
            message: detail || 'A user with this owner email already exists.',
          });
        } else {
          setGeneralError(detail || 'Conflict: Organization or user already exists.');
        }
      } else if (status === 400) {
        setGeneralError(detail || 'Validation error occurred while creating organization.');
      } else {
        setGeneralError(detail || 'Failed to create organization. Please try again.');
      }
    }
  };

  const handleCopyPassword = () => {
    if (tempPasswordModal?.password) {
      navigator.clipboard.writeText(tempPasswordModal.password);
      setHasCopiedPassword(true);
      toast.info('Temporary password copied to clipboard.');
      setTimeout(() => setHasCopiedPassword(false), 3000);
    }
  };

  const handleDismissSuccessDialog = () => {
    setTempPasswordModal(null);
    setHasCopiedPassword(false);
    loadTenants();
  };

  // --- Owner Action Handlers ---
  const handleOpenEditOwner = (tenant: Tenant) => {
    setEditOwnerTenant(tenant);
    setEditOwnerForm({
      name: tenant.owner_name || tenant.contact_person_name || '',
      email: tenant.owner_email || tenant.contact_email || '',
      phone_number: tenant.owner_phone || tenant.phone_number || '',
    });
    setEditOwnerErrors({});
  };

  const handleCloseEditOwner = () => {
    setEditOwnerTenant(null);
    setEditOwnerErrors({});
  };

  const handleSubmitEditOwner = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editOwnerTenant) return;
    const errors: Record<string, string> = {};
    if (!editOwnerForm.name.trim()) {
      errors.name = 'Owner name is required.';
    }
    if (!editOwnerForm.email.trim()) {
      errors.email = 'Owner email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editOwnerForm.email.trim())) {
      errors.email = 'Please enter a valid email address.';
    }
    if (editOwnerForm.phone_number.trim() && !/^(\+91[\-\s]?)?[6-9]\d{9}$/.test(editOwnerForm.phone_number.trim())) {
      errors.phone_number = 'Phone number must be a valid Indian number (10 digits starting with 6, 7, 8 or 9, optional +91)';
    }
    if (Object.keys(errors).length > 0) {
      setEditOwnerErrors(errors);
      return;
    }

    setIsSubmittingEdit(true);
    setEditOwnerErrors({});
    try {
      await adminService.editTenantOwner(editOwnerTenant.tenant_id, {
        name: editOwnerForm.name.trim(),
        email: editOwnerForm.email.trim().toLowerCase(),
        phone_number: editOwnerForm.phone_number.trim() || undefined,
      });
      toast.success('Organization Owner updated successfully.');
      handleCloseEditOwner();
      loadTenants();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || err?.message || 'Failed to update owner.';
      if (status === 409) {
        setEditOwnerErrors({ email: detail || 'A user with this email address already exists.' });
      } else {
        setEditOwnerErrors({ general: detail });
      }
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleOpenResetPassword = (tenant: Tenant) => {
    setResetOwnerTenant(tenant);
  };

  const handleConfirmResetPassword = async () => {
    if (!resetOwnerTenant) return;
    setIsSubmittingReset(true);
    try {
      const res = await adminService.resetTenantOwnerPassword(resetOwnerTenant.tenant_id);
      const tempPass = res.temporary_password || '';
      const email = res.email || resetOwnerTenant.owner_email || '';
      const org = resetOwnerTenant.business_name || resetOwnerTenant.name;
      setResetOwnerTenant(null);
      setTempPasswordModal({
        title: 'Temporary Password Generated',
        subtitle: 'Organization Owner credentials have been reset.',
        organization: org,
        email: email,
        password: tempPass,
      });
      toast.success('Organization Owner password reset successfully.');
      loadTenants();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to reset password.');
    } finally {
      setIsSubmittingReset(false);
    }
  };

  const handleOpenDeactivateOwner = (tenant: Tenant) => {
    setDeactivateOwnerTenant(tenant);
  };

  const handleConfirmDeactivateOwner = async () => {
    if (!deactivateOwnerTenant) return;
    setIsSubmittingDeactivate(true);
    try {
      const res = await adminService.toggleTenantOwnerActive(deactivateOwnerTenant.tenant_id, false);
      toast.info(res.warning || 'Organization Owner deactivated. This organization has no active owner until replaced.');
      setDeactivateOwnerTenant(null);
      loadTenants();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to deactivate owner.');
    } finally {
      setIsSubmittingDeactivate(false);
    }
  };

  const handleReactivateOwner = async (tenant: Tenant) => {
    try {
      await adminService.toggleTenantOwnerActive(tenant.tenant_id, true);
      toast.success('Organization Owner reactivated successfully.');
      loadTenants();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to reactivate owner.');
    }
  };

  const handleOpenReplaceOwner = (tenant: Tenant) => {
    setReplaceOwnerTenant(tenant);
    setReplaceOwnerForm({ name: '', email: '', phone_number: '' });
    setReplaceOwnerErrors({});
  };

  const handleCloseReplaceOwner = () => {
    setReplaceOwnerTenant(null);
    setReplaceOwnerErrors({});
  };

  const handleSubmitReplaceOwner = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replaceOwnerTenant) return;
    const errors: Record<string, string> = {};
    if (!replaceOwnerForm.name.trim()) {
      errors.name = 'New owner name is required.';
    }
    if (!replaceOwnerForm.email.trim()) {
      errors.email = 'New owner email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(replaceOwnerForm.email.trim())) {
      errors.email = 'Please enter a valid email address.';
    }
    if (replaceOwnerForm.phone_number.trim() && !/^(\+91[\-\s]?)?[6-9]\d{9}$/.test(replaceOwnerForm.phone_number.trim())) {
      errors.phone_number = 'Phone number must be a valid Indian number (10 digits starting with 6, 7, 8 or 9, optional +91)';
    }
    if (Object.keys(errors).length > 0) {
      setReplaceOwnerErrors(errors);
      return;
    }

    setIsSubmittingReplace(true);
    setReplaceOwnerErrors({});
    try {
      const res = await adminService.replaceTenantOwner(replaceOwnerTenant.tenant_id, {
        name: replaceOwnerForm.name.trim(),
        email: replaceOwnerForm.email.trim().toLowerCase(),
        phone_number: replaceOwnerForm.phone_number.trim() || undefined,
      });
      const org = replaceOwnerTenant.business_name || replaceOwnerTenant.name;
      handleCloseReplaceOwner();
      setTempPasswordModal({
        title: 'New Organization Owner Provisioned',
        subtitle: 'The previous owner was replaced and new credentials have been generated.',
        organization: org,
        email: res.email,
        password: res.temporary_password || '',
      });
      toast.success('Organization Owner replaced successfully.');
      loadTenants();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || err?.message || 'Failed to replace owner.';
      if (status === 409) {
        setReplaceOwnerErrors({ email: detail });
      } else {
        setReplaceOwnerErrors({ general: detail });
      }
    } finally {
      setIsSubmittingReplace(false);
    }
  };

  const handleToggleDeactivate = async (tenantId: string) => {
    if (!isAdmin) return;
    try {
      const res = await adminService.deactivateTenant(tenantId);
      await loadTenants();
      toast.info(`Organization status updated to ${res.is_active ? 'Active' : 'Deactivated'}.`);
    } catch {
      toast.error('Failed to update organization status.');
    }
  };

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const filteredTenants = useMemo(() => {
    return tenants.filter((t) => {
      const name = t.business_name || t.name || '';
      const email = t.contact_email || '';
      const slug = t.slug || '';
      const query = searchQuery.toLowerCase();
      return (
        query === '' ||
        name.toLowerCase().includes(query) ||
        email.toLowerCase().includes(query) ||
        slug.toLowerCase().includes(query)
      );
    });
  }, [tenants, searchQuery]);

  const paginatedTenants = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredTenants.slice(start, start + pageSize);
  }, [filteredTenants, currentPage, pageSize]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-helios-border-light dark:border-helios-border-dark">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Organization Directory
          </h1>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            {isAdmin
              ? 'Global registry of customer organizations and organization lifecycle.'
              : 'Directory of your assigned customer organizations.'}
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

          {/* Add New Organization Button - Available to BOTH Team Member and Admin */}
          <button
            type="button"
            onClick={handleOpenModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Organization</span>
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
        <input
          type="text"
          placeholder="Search by business name or email"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder:text-helios-text-secondary-light dark:placeholder:text-helios-text-secondary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all"
        />
      </div>

      {/* Organizations Table */}
      <div className="rounded-2xl border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark overflow-hidden shadow-soft">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/5 dark:bg-white/5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                <th className="py-3 px-4">Organization / Business</th>
                <th className="py-3 px-4">Industry</th>
                <th className="py-3 px-4">Contact & Phone</th>
                <th className="py-3 px-4">Organization Owner</th>
                <th className="py-3 px-4">Location / Address</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <RefreshCw className="w-5 h-5 mx-auto animate-spin mb-2 text-helios-accent-blue" />
                    <span>Loading organization directory...</span>
                  </td>
                </tr>
              ) : displayError ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-rose-500">
                    <p className="font-semibold text-sm">{displayError}</p>
                    <button
                      type="button"
                      onClick={loadTenants}
                      className="mt-3 px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20"
                    >
                      Retry
                    </button>
                  </td>
                </tr>
              ) : paginatedTenants.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <Building2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="font-semibold text-sm">
                      {searchQuery
                        ? 'No organizations found'
                        : (!isAdmin
                            ? 'No organizations are assigned to you yet. Contact your admin.'
                            : 'No organizations found')}
                    </p>
                    <p className="text-xs mt-1">
                      {searchQuery
                        ? 'Try adjusting your search query.'
                        : (isAdmin ? 'Onboard a new organization to get started.' : '')}
                    </p>
                  </td>
                </tr>
              ) : (
                paginatedTenants.map((t) => {
                  const displayName = t.business_name || t.name;
                  return (
                    <tr
                      key={t.tenant_id}
                      className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors group"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-helios-accent-blue/10 flex items-center justify-center text-helios-accent-blue font-bold">
                            {displayName.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                              {displayName}
                            </div>
                            <div className="text-[11px] font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                              ID: {t.tenant_id}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        {t.industry || '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="text-helios-text-primary-light dark:text-helios-text-primary-dark font-medium">
                          {t.contact_person_name || '—'}
                        </div>
                        <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          {t.contact_email || '—'}
                        </div>
                        {t.phone_number && (
                          <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                            {t.phone_number}
                          </div>
                        )}
                        {t.website_url && (
                          <a
                            href={t.website_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] text-helios-accent-blue hover:underline block truncate max-w-[160px]"
                          >
                            {t.website_url.replace(/^https?:\/\//, '')}
                          </a>
                        )}
                      </td>
                      {/* Organization Owner Column */}
                      <td className="py-3.5 px-4">
                        {t.owner_id ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                                {t.owner_name || '—'}
                              </span>
                              <span
                                className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
                                  t.owner_is_active
                                    ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                    : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                                }`}
                              >
                                <span className={`w-1 h-1 rounded-full ${t.owner_is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                {t.owner_is_active ? 'Active' : 'Inactive'}
                              </span>
                            </div>
                            <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-mono truncate max-w-[180px]">
                              {t.owner_email || '—'}
                            </div>
                            {t.owner_phone && (
                              <div className="text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                                {t.owner_phone}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] italic text-amber-500">No Owner</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {t.address_line1 || '—'}
                          {t.address_line2 ? `, ${t.address_line2}` : ''}
                        </div>
                        <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          {[t.city, t.state, t.postal_code].filter(Boolean).join(', ')}
                          {t.country ? ` · ${t.country}` : ''}
                        </div>
                        {t.tax_id && (
                          <div className="text-[10px] font-mono text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                            GSTIN: {t.tax_id}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                            t.is_active
                              ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${t.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                          {t.is_active ? 'Active' : 'Deactivated'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark text-[11px]">
                        {t.created_at ? formatDateIN(t.created_at) : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Edit Owner */}
                          <button
                            type="button"
                            onClick={() => handleOpenEditOwner(t)}
                            title="Edit Organization Owner"
                            className="p-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-accent-blue hover:border-helios-accent-blue/30 hover:bg-helios-accent-blue/10 transition-colors"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          {/* Reset Password */}
                          <button
                            type="button"
                            onClick={() => handleOpenResetPassword(t)}
                            title="Reset Organization Owner Password"
                            className="p-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-amber-500 hover:border-amber-500/30 hover:bg-amber-500/10 transition-colors"
                          >
                            <Key className="w-3.5 h-3.5" />
                          </button>

                          {/* Deactivate or Reactivate Owner */}
                          {t.owner_is_active ? (
                            <button
                              type="button"
                              onClick={() => handleOpenDeactivateOwner(t)}
                              title="Deactivate Organization Owner"
                              className="p-1.5 rounded-lg border border-rose-500/20 text-rose-500 hover:bg-rose-500/10 transition-colors"
                            >
                              <UserX className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleReactivateOwner(t)}
                              title="Reactivate Organization Owner"
                              className="p-1.5 rounded-lg border border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/10 transition-colors"
                            >
                              <UserCheck className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* Replace Owner: Enabled ONLY when owner is inactive */}
                          <button
                            type="button"
                            onClick={() => handleOpenReplaceOwner(t)}
                            disabled={Boolean(t.owner_is_active)}
                            title={
                              t.owner_is_active
                                ? 'Replace Organization Owner (Owner must be deactivated first)'
                                : 'Replace Inactive Organization Owner'
                            }
                            className={`p-1.5 rounded-lg border transition-colors ${
                              t.owner_is_active
                                ? 'opacity-30 cursor-not-allowed border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark'
                                : 'border-blue-500/30 text-blue-500 hover:bg-blue-500/10 cursor-pointer'
                            }`}
                          >
                            <UserPlus className="w-3.5 h-3.5" />
                          </button>

                          {/* Admin Only: Toggle Organization Active */}
                          {isAdmin && (
                            <button
                              type="button"
                              onClick={() => handleToggleDeactivate(t.tenant_id)}
                              title={t.is_active ? 'Deactivate Organization' : 'Activate Organization'}
                              className={`p-1.5 rounded-lg border transition-colors ml-1 ${
                                t.is_active
                                  ? 'border-rose-500/20 text-rose-500 hover:bg-rose-500/10'
                                  : 'border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/10'
                              }`}
                            >
                              <Power className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!isLoading && filteredTenants.length > pageSize && (
          <div className="p-4 border-t border-helios-border-light dark:border-helios-border-dark flex items-center justify-between">
            <Pagination
              currentPage={currentPage}
              totalItems={filteredTenants.length}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* Complete "Add Organization" Modal                                        */}
      {/* Three clearly labeled sections (Business, Contact, Address) + Assignment  */}
      {/* ========================================================================= */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn overflow-y-auto">
          <div className="w-full max-w-2xl my-8 p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-helios-accent-blue/15 flex items-center justify-center text-helios-accent-blue">
                  <Building2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Onboard New Organization
                  </h3>
                  <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Complete onboarding details and provision Organization Owner portal credentials.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseModal}
                className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark p-1 rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* General Banner Error */}
            {generalError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{generalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 text-xs" noValidate>
              {/* SECTION 1: Business Details */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <Building2 className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>Business Information</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {/* Business Name (required) */}
                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Business Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Acme Consumer Goods Ltd"
                      {...register('business_name')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.business_name
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.business_name && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.business_name.message}
                      </p>
                    )}
                  </div>

                  {/* Industry (required dropdown) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Industry <span className="text-rose-500">*</span>
                    </label>
                    <select
                      {...register('industry')}
                      className={`w-full px-3 py-2 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.industry
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    >
                      <option value="">Select an industry...</option>
                      {INDUSTRY_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                    {errors.industry && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.industry.message}
                      </p>
                    )}
                  </div>

                  {/* GSTIN (optional) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      GSTIN <span className="text-slate-400 font-normal">(Optional, 15 characters)</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 29ABCDE1234F1Z5"
                      maxLength={15}
                      {...register('tax_id')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border uppercase text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.tax_id
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.tax_id && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.tax_id.message}
                      </p>
                    )}
                  </div>

                  {/* Website URL (optional) */}
                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Website URL <span className="text-slate-400 font-normal">(Optional, http:// or https://)</span>
                    </label>
                    <div className="relative">
                      <Globe className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <input
                        type="url"
                        placeholder="https://www.example.com"
                        {...register('website_url')}
                        className={`w-full pl-9 pr-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                          errors.website_url
                            ? 'border-rose-500 focus:ring-rose-500'
                            : 'border-helios-border-light dark:border-helios-border-dark'
                        }`}
                      />
                    </div>
                    {errors.website_url && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.website_url.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* SECTION 2: Contact Person & Owner Login */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <User className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>Contact & Login Credentials</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {/* Contact Person Name (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Contact Person Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Aarav Sharma"
                      {...register('contact_person_name')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.contact_person_name
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.contact_person_name && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.contact_person_name.message}
                      </p>
                    )}
                  </div>

                  {/* Phone Number (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Phone Number <span className="text-rose-500">*</span>
                    </label>
                    <div className="relative">
                      <Phone className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <input
                        type="tel"
                        placeholder="e.g. +91 9876543210 or 9876543210"
                        {...register('phone_number')}
                        className={`w-full pl-9 pr-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                          errors.phone_number
                            ? 'border-rose-500 focus:ring-rose-500'
                            : 'border-helios-border-light dark:border-helios-border-dark'
                        }`}
                      />
                    </div>
                    {errors.phone_number && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.phone_number.message}
                      </p>
                    )}
                  </div>

                  {/* Contact Email (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Contact Email <span className="text-rose-500">*</span>
                    </label>
                    <div className="relative">
                      <Mail className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <input
                        type="email"
                        placeholder="contact@company.in"
                        value={contactEmailValue}
                        onChange={handleContactEmailChange}
                        className={`w-full pl-9 pr-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                          errors.contact_email
                            ? 'border-rose-500 focus:ring-rose-500'
                            : 'border-helios-border-light dark:border-helios-border-dark'
                        }`}
                      />
                    </div>
                    {errors.contact_email && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.contact_email.message}
                      </p>
                    )}
                  </div>

                  {/* Owner Login Email (required, defaults to contact email) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Organization Owner Login Email <span className="text-rose-500">*</span>
                    </label>
                    <div className="relative">
                      <Lock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <input
                        type="email"
                        placeholder="owner@company.in"
                        {...register('owner_email')}
                        className={`w-full pl-9 pr-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                          errors.owner_email
                            ? 'border-rose-500 focus:ring-rose-500'
                            : 'border-helios-border-light dark:border-helios-border-dark'
                        }`}
                      />
                    </div>
                    {errors.owner_email && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.owner_email.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* SECTION 3: Physical Address */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                  <MapPin className="w-3.5 h-3.5 text-helios-accent-blue" />
                  <span>Business Address</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {/* Address Line 1 (required) */}
                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Address Line 1 <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Street address, building, company location"
                      {...register('address_line1')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.address_line1
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.address_line1 && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.address_line1.message}
                      </p>
                    )}
                  </div>

                  {/* Address Line 2 (optional) */}
                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Address Line 2 <span className="text-slate-400 font-normal">(Apartment, suite, unit, floor)</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Suite 400"
                      {...register('address_line2')}
                      className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    />
                  </div>

                  {/* City (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      City <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Bengaluru"
                      {...register('city')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.city
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.city && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.city.message}</p>
                    )}
                  </div>

                  {/* State / Union Territory (required dropdown) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      State / Union Territory <span className="text-rose-500">*</span>
                    </label>
                    <select
                      {...register('state')}
                      className={`w-full px-3 py-2 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.state
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    >
                      <option value="">Select State / UT...</option>
                      {INDIAN_STATES_AND_UTS.map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                    {errors.state && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.state.message}</p>
                    )}
                  </div>

                  {/* PIN code (required, 6 digits) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      PIN code <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 560001"
                      maxLength={6}
                      {...register('postal_code')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.postal_code
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.postal_code && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.postal_code.message}
                      </p>
                    )}
                  </div>

                  {/* Country (fixed, read-only) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Country <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      readOnly
                      value="India"
                      {...register('country')}
                      className="w-full px-3 py-2 rounded-xl bg-black/10 dark:bg-white/10 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark cursor-not-allowed opacity-80"
                    />
                    {errors.country && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">
                        {errors.country.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* SECTION 4: Team Member Assignment (Admin only) */}
              {isAdmin && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark border-b border-helios-border-light/60 dark:border-helios-border-dark/60 pb-1.5">
                    <UserCheck className="w-3.5 h-3.5 text-helios-accent-blue" />
                    <span>Operations Assignment (Admin Only)</span>
                  </div>

                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Assign to Team Member <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <select
                      {...register('assigned_team_member_id')}
                      className="w-full px-3 py-2 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    >
                      <option value="">None / Unassigned</option>
                      {teamMembers.map((tm) => (
                        <option key={tm.user_id} value={tm.user_id}>
                          {tm.name} ({tm.email})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Form Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50"
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
                      <span>Provisioning Organization...</span>
                    </>
                  ) : (
                    <span>Onboard Organization</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Edit SMB Owner Modal                                                      */}
      {/* ========================================================================= */}
      {editOwnerTenant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-helios-accent-blue/15 flex items-center justify-center text-helios-accent-blue">
                  <Edit2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Edit Organization Owner
                  </h3>
                  <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Update contact details for {editOwnerTenant.business_name || editOwnerTenant.name}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseEditOwner}
                className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark p-1 rounded-lg transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {editOwnerErrors.general && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{editOwnerErrors.general}</span>
              </div>
            )}

            <form onSubmit={handleSubmitEditOwner} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={editOwnerForm.name}
                  onChange={(e) => setEditOwnerForm({ ...editOwnerForm, name: e.target.value })}
                  placeholder="e.g. Jane Doe"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    editOwnerErrors.name
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {editOwnerErrors.name && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{editOwnerErrors.name}</p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={editOwnerForm.email}
                  onChange={(e) => setEditOwnerForm({ ...editOwnerForm, email: e.target.value })}
                  placeholder="owner@business.com"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    editOwnerErrors.email
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {editOwnerErrors.email && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{editOwnerErrors.email}</p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={editOwnerForm.phone_number}
                  onChange={(e) => setEditOwnerForm({ ...editOwnerForm, phone_number: e.target.value })}
                  placeholder="e.g. +91 9876543210 or 9876543210"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    editOwnerErrors.phone_number
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {editOwnerErrors.phone_number && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{editOwnerErrors.phone_number}</p>
                )}
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={handleCloseEditOwner}
                  disabled={isSubmittingEdit}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-black/5 dark:bg-white/5 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/10 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEdit}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all disabled:opacity-50"
                >
                  {isSubmittingEdit && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Reset Password Confirmation Modal                                         */}
      {/* ========================================================================= */}
      {resetOwnerTenant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500">
                <Key className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Reset Organization Owner Password
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Generate a new temporary password for this owner account.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Organization:</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {resetOwnerTenant.business_name || resetOwnerTenant.name}
                </span>
              </div>
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Owner:</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {resetOwnerTenant.owner_name || '—'}
                </span>
              </div>
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Email:</span>
                <span className="font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {resetOwnerTenant.owner_email || '—'}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-500 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                A new temporary password will be created and displayed once. The owner will be required to change it upon next login.
              </span>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-helios-border-light dark:border-helios-border-dark">
              <button
                type="button"
                onClick={() => setResetOwnerTenant(null)}
                disabled={isSubmittingReset}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-black/5 dark:bg-white/5 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/10 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmResetPassword}
                disabled={isSubmittingReset}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-amber-500 hover:bg-amber-600 text-white shadow-sm transition-all disabled:opacity-50"
              >
                {isSubmittingReset && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Generate Temporary Password</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Deactivate SMB Owner Confirmation Modal                                    */}
      {/* ========================================================================= */}
      {deactivateOwnerTenant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-500">
                <UserX className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Deactivate Organization Owner
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  {deactivateOwnerTenant.owner_name} ({deactivateOwnerTenant.owner_email})
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-600 dark:text-amber-400 text-xs flex items-start gap-2.5 leading-relaxed">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-500" />
              <div>
                <strong className="block mb-0.5">Warning:</strong>
                This organization has no active owner until replaced. Deactivating will revoke owner access to the portal immediately.
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-helios-border-light dark:border-helios-border-dark">
              <button
                type="button"
                onClick={() => setDeactivateOwnerTenant(null)}
                disabled={isSubmittingDeactivate}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-black/5 dark:bg-white/5 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/10 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeactivateOwner}
                disabled={isSubmittingDeactivate}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-rose-500 hover:bg-rose-600 text-white shadow-sm transition-all disabled:opacity-50"
              >
                {isSubmittingDeactivate && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Deactivate Owner</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Replace SMB Owner Modal (Enabled only when current owner is inactive)      */}
      {/* ========================================================================= */}
      {replaceOwnerTenant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-helios-accent-blue/15 flex items-center justify-center text-helios-accent-blue">
                  <UserPlus className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Replace Organization Owner
                  </h3>
                  <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Provision replacement owner for {replaceOwnerTenant.business_name || replaceOwnerTenant.name}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseReplaceOwner}
                className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark p-1 rounded-lg transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {replaceOwnerErrors.general && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{replaceOwnerErrors.general}</span>
              </div>
            )}

            <form onSubmit={handleSubmitReplaceOwner} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  New Owner Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={replaceOwnerForm.name}
                  onChange={(e) => setReplaceOwnerForm({ ...replaceOwnerForm, name: e.target.value })}
                  placeholder="e.g. Aarav Sharma"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    replaceOwnerErrors.name
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {replaceOwnerErrors.name && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{replaceOwnerErrors.name}</p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  New Owner Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={replaceOwnerForm.email}
                  onChange={(e) => setReplaceOwnerForm({ ...replaceOwnerForm, email: e.target.value })}
                  placeholder="newowner@business.in"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    replaceOwnerErrors.email
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {replaceOwnerErrors.email && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{replaceOwnerErrors.email}</p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={replaceOwnerForm.phone_number}
                  onChange={(e) => setReplaceOwnerForm({ ...replaceOwnerForm, phone_number: e.target.value })}
                  placeholder="e.g. +91 9876543210 or 9876543210"
                  className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                    replaceOwnerErrors.phone_number
                      ? 'border-rose-500 focus:ring-rose-500'
                      : 'border-helios-border-light dark:border-helios-border-dark'
                  }`}
                />
                {replaceOwnerErrors.phone_number && (
                  <p className="mt-1 text-[11px] text-rose-500 font-medium">{replaceOwnerErrors.phone_number}</p>
                )}
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={handleCloseReplaceOwner}
                  disabled={isSubmittingReplace}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-black/5 dark:bg-white/5 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/10 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReplace}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all disabled:opacity-50"
                >
                  {isSubmittingReplace && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Replace Owner</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Unified Success Dialog: Generated Temporary Password (Shown ONCE)        */}
      {/* ========================================================================= */}
      {tempPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {tempPasswordModal.title}
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  {tempPasswordModal.subtitle}
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark space-y-2 text-xs">
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Organization:</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {tempPasswordModal.organization}
                </span>
              </div>
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Organization Owner Login:</span>
                <span className="font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {tempPasswordModal.email}
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
                  {tempPasswordModal.password || '********'}
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

            {/* Warning Note */}
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-500 text-xs flex items-start gap-2 leading-relaxed">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Important:</strong> This temporary password will <strong>not</strong> be shown again.
                Please copy and transmit it securely to the organization owner.
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
    </div>
  );
};

export default Tenants;
