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
} from 'lucide-react';
import { Tenant, TeamMember } from '@/types/admin';
import { adminService } from '@/services/adminService';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/Toast';
import { Pagination } from '@/components/ui/Pagination';

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
  tax_id: z.string().optional(),

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
    .min(7, 'Phone number must be at least 7 characters')
    .max(20, 'Phone number cannot exceed 20 characters')
    .regex(
      /^[0-9+\-() ]{7,20}$/,
      'Phone number must contain only digits, spaces, plus, dash, and parentheses'
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
  state: z.string().min(1, 'State is required').max(100),
  postal_code: z.string().min(1, 'Postal code is required').max(20),
  country: z.string().min(1, 'Country is required').max(100),

  // Assignment Section (Admin only)
  assigned_team_member_id: z.string().optional(),
});

type TenantFormValues = z.infer<typeof tenantFormSchema>;

export const Tenants: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const toast = useToast();

  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Temporary password success dialog state
  const [createdTenantResult, setCreatedTenantResult] = useState<Tenant | null>(null);
  const [hasCopiedPassword, setHasCopiedPassword] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

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
      country: '',
      assigned_team_member_id: '',
    },
  });

  const contactEmailValue = watch('contact_email');
  const ownerEmailValue = watch('owner_email');

  // Load tenants
  const loadTenants = async () => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const data = await adminService.getTenants();
      if (!isAdmin && user) {
        const assigned = (user as any).assigned_tenants || [];
        setTenants(data.filter((t) => assigned.includes(String(t.tenant_id)) || assigned.includes(t.slug)));
      } else {
        setTenants(data);
      }
    } catch (err: any) {
      setGeneralError(err?.response?.data?.detail || err.message || 'Failed to load tenants.');
    } finally {
      setIsLoading(false);
    }
  };

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

  useEffect(() => {
    loadTenants();
  }, [isAdmin, user]);

  // Handle contact email blur/change to default owner_email if untouched
  const handleContactEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setValue('contact_email', val, { shouldValidate: true });
    if (!ownerEmailValue || ownerEmailValue === contactEmailValue) {
      setValue('owner_email', val, { shouldValidate: true });
    }
  };

  const handleOpenModal = () => {
    reset();
    setGeneralError(null);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    reset();
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
        country: data.country.trim(),
        assigned_team_member_id: assignedIdNum,
      });

      // Close onboarding modal and show temporary password dialog
      setShowModal(false);
      setCreatedTenantResult(newTenant);
      setHasCopiedPassword(false);
      toast.success(
        `Tenant "${data.business_name}" onboarded successfully.`,
        'Tenant Provisioned'
      );
      // Refresh list
      loadTenants();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || err?.message || '';

      if (status === 409) {
        const detailLower = detail.toLowerCase();
        if (detailLower.includes('business') || detailLower.includes('tenant')) {
          setError('business_name', {
            type: 'manual',
            message: detail || 'An active tenant with this business name already exists.',
          });
        } else if (detailLower.includes('email') || detailLower.includes('user')) {
          setError('owner_email', {
            type: 'manual',
            message: detail || 'A user with this owner email already exists.',
          });
        } else {
          setGeneralError(detail || 'Conflict: Tenant or user already exists.');
        }
      } else if (status === 400) {
        setGeneralError(detail || 'Validation error occurred while creating tenant.');
      } else {
        setGeneralError(detail || 'Failed to create tenant. Please try again.');
      }
    }
  };

  const handleCopyPassword = () => {
    if (createdTenantResult?.temporary_password) {
      navigator.clipboard.writeText(createdTenantResult.temporary_password);
      setHasCopiedPassword(true);
      toast.info('Temporary password copied to clipboard.');
      setTimeout(() => setHasCopiedPassword(false), 3000);
    }
  };

  const handleDismissSuccessDialog = () => {
    setCreatedTenantResult(null);
    setHasCopiedPassword(false);
    loadTenants();
  };

  const handleToggleDeactivate = async (tenantId: string) => {
    if (!isAdmin) return;
    try {
      const res = await adminService.deactivateTenant(tenantId);
      setTenants((prev) =>
        prev.map((t) => (t.tenant_id === tenantId ? { ...t, is_active: res.is_active } : t))
      );
      toast.info(`Tenant status updated to ${res.is_active ? 'Active' : 'Deactivated'}.`);
    } catch {
      toast.error('Failed to update tenant status.');
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
            onClick={handleOpenModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue hover:bg-blue-600 text-white shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Tenant</span>
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
        <input
          type="text"
          placeholder="Search by business name, email, or slug..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder:text-helios-text-secondary-light dark:placeholder:text-helios-text-secondary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all"
        />
      </div>

      {/* Tenants Table */}
      <div className="rounded-2xl border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark overflow-hidden shadow-soft">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-black/5 dark:bg-white/5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                <th className="py-3 px-4">Organization / Business</th>
                <th className="py-3 px-4">Industry</th>
                <th className="py-3 px-4">Contact</th>
                <th className="py-3 px-4">Catalog / Schema</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                {isAdmin && <th className="py-3 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
              {isLoading ? (
                <tr>
                  <td colSpan={isAdmin ? 7 : 6} className="py-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <RefreshCw className="w-5 h-5 mx-auto animate-spin mb-2 text-helios-accent-blue" />
                    <span>Loading tenant directory...</span>
                  </td>
                </tr>
              ) : generalError ? (
                <tr>
                  <td colSpan={isAdmin ? 7 : 6} className="py-12 text-center text-rose-500">
                    <p className="font-semibold text-sm">{generalError}</p>
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
                  <td colSpan={isAdmin ? 7 : 6} className="py-12 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <Building2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="font-semibold text-sm">No tenants found</p>
                    <p className="text-xs mt-1">Try adjusting your search query or onboard a new tenant organization.</p>
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
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        {t.catalog_name || 'helios_catalog'}.{t.schema_name || 'default'}
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
                        {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                      </td>
                      {isAdmin && (
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => handleToggleDeactivate(t.tenant_id)}
                            title={t.is_active ? 'Deactivate Tenant' : 'Activate Tenant'}
                            className={`p-1.5 rounded-lg border transition-colors ${
                              t.is_active
                                ? 'border-rose-500/20 text-rose-500 hover:bg-rose-500/10'
                                : 'border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/10'
                            }`}
                          >
                            <Power className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      )}
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
      {/* Complete "Add New Tenant" Modal                                           */}
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
                    Onboard New Tenant Organization
                  </h3>
                  <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Complete onboarding details and provision SMB Owner portal credentials.
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

                  {/* Tax ID (optional) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Tax ID / EIN <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. US-123456789"
                      {...register('tax_id')}
                      className="w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    />
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
                      placeholder="e.g. Jane Doe"
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
                        placeholder="+1 (555) 019-2834"
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
                        placeholder="jane@company.com"
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
                      Owner Login Email <span className="text-rose-500">*</span>
                    </label>
                    <div className="relative">
                      <Lock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                      <input
                        type="email"
                        placeholder="owner@company.com"
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
                      placeholder="Street address, P.O. box, company name"
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
                      placeholder="e.g. Austin"
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

                  {/* State / Province (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      State / Province <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Texas"
                      {...register('state')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.state
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
                    />
                    {errors.state && (
                      <p className="mt-1 text-[11px] text-rose-500 font-medium">{errors.state.message}</p>
                    )}
                  </div>

                  {/* Postal / ZIP Code (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Postal / ZIP Code <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 78701"
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

                  {/* Country (required) */}
                  <div>
                    <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                      Country <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. United States"
                      {...register('country')}
                      className={`w-full px-3 py-2 rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue ${
                        errors.country
                          ? 'border-rose-500 focus:ring-rose-500'
                          : 'border-helios-border-light dark:border-helios-border-dark'
                      }`}
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
                      <span>Provisioning Tenant...</span>
                    </>
                  ) : (
                    <span>Onboard Tenant</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Success Dialog: Display Generated Temporary Password (Shown ONCE)        */}
      {/* ========================================================================= */}
      {createdTenantResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Tenant Onboarded Successfully
                </h3>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  SMB Owner credentials have been generated.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark space-y-2 text-xs">
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>Organization:</span>
                <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {createdTenantResult.business_name || createdTenantResult.name}
                </span>
              </div>
              <div className="flex justify-between items-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <span>SMB Owner Login:</span>
                <span className="font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {createdTenantResult.owner_email || createdTenantResult.contact_email}
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
                  {createdTenantResult.temporary_password || '********'}
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
                Please copy and transmit it securely to the business owner.
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
