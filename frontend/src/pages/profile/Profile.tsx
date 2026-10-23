import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Building2,
  Users,
  Shield,
  KeyRound,
  Mail,
  Phone,
  Globe,
  MapPin,
  Calendar,
  Briefcase,
  IdCard,
  Clock,
  RefreshCw,
  AlertTriangle,
  Building,
  Activity,
  UserCheck,
  Edit3,
  Save,
  X,
  AlertCircle,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { profileService } from '@/services/profileService';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/Toast';
import {
  ProfileData,
  OwnerProfileData,
  TeamMemberProfileData,
  AdminProfileData,
} from '@/types/profile';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { formatDateIN, formatDateTimeIN, formatCountIN } from '@/utils/currency';

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

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const toast = useToast();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Edit states
  const [isEditingDetails, setIsEditingDetails] = useState<boolean>(false);
  const [detailsForm, setDetailsForm] = useState({ name: '', phone: '' });
  const [detailsErrors, setDetailsErrors] = useState<{ name?: string; phone?: string }>({});
  const [savingDetails, setSavingDetails] = useState<boolean>(false);

  const [isEditingOrg, setIsEditingOrg] = useState<boolean>(false);
  const [orgForm, setOrgForm] = useState({
    contact_person_name: '',
    phone_number: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    website_url: '',
    tax_id: '',
  });
  const [orgErrors, setOrgErrors] = useState<Record<string, string>>({});
  const [savingOrg, setSavingOrg] = useState<boolean>(false);

  // Email Change Modal state
  const [showEmailModal, setShowEmailModal] = useState<boolean>(false);
  const [emailForm, setEmailForm] = useState({ new_email: '', current_password: '' });
  const [emailErrors, setEmailErrors] = useState<{ new_email?: string; current_password?: string; general?: string }>({});
  const [savingEmail, setSavingEmail] = useState<boolean>(false);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await profileService.getProfile();
      setProfile(data);
      // Initialize edit forms with fetched data
      setDetailsForm({
        name: data.me.name || '',
        phone: data.me.phone || '',
      });
      if (data.role === 'smb_owner' && (data as OwnerProfileData).organization) {
        const org = (data as OwnerProfileData).organization!;
        setOrgForm({
          contact_person_name: org.contact_person || '',
          phone_number: org.phone || '',
          address_line1: org.address_line1 || '',
          address_line2: org.address_line2 || '',
          city: org.city || '',
          state: org.state || '',
          postal_code: org.pin_code || '',
          website_url: org.website || '',
          tax_id: org.gstin || '',
        });
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(detail || 'Failed to load profile details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  // Warn if leaving page with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isEditingDetails || isEditingOrg) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isEditingDetails, isEditingOrg]);

  // Validation functions
  const validateDetails = (): boolean => {
    const errs: { name?: string; phone?: string } = {};
    const trimmedName = detailsForm.name.trim();
    if (!trimmedName || trimmedName.length < 2) {
      errs.name = 'Full name must be at least 2 characters';
    } else if (trimmedName.length > 100) {
      errs.name = 'Full name cannot exceed 100 characters';
    }

    if (detailsForm.phone && detailsForm.phone.trim()) {
      const trimmedPhone = detailsForm.phone.trim();
      const phoneRegex = /^(\+91[\-\s]?)?[6-9]\d{9}$/;
      if (!phoneRegex.test(trimmedPhone)) {
        errs.phone = 'Phone number must be a valid 10-digit Indian number starting with 6-9 (optional +91)';
      }
    }

    setDetailsErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const validateOrg = (): boolean => {
    const errs: Record<string, string> = {};

    if (orgForm.contact_person_name && orgForm.contact_person_name.trim()) {
      const cp = orgForm.contact_person_name.trim();
      if (cp.length < 2) errs.contact_person_name = 'Contact person name must be at least 2 characters';
      if (cp.length > 100) errs.contact_person_name = 'Contact person name cannot exceed 100 characters';
    }

    if (orgForm.phone_number && orgForm.phone_number.trim()) {
      const p = orgForm.phone_number.trim();
      const phoneRegex = /^(\+91[\-\s]?)?[6-9]\d{9}$/;
      if (!phoneRegex.test(p)) {
        errs.phone_number = 'Phone number must be a valid 10-digit Indian number starting with 6-9 (optional +91)';
      }
    }

    if (orgForm.address_line1 && orgForm.address_line1.trim()) {
      const a1 = orgForm.address_line1.trim();
      if (a1.length < 2) errs.address_line1 = 'Address line 1 must be at least 2 characters';
      if (a1.length > 200) errs.address_line1 = 'Address line 1 cannot exceed 200 characters';
    }

    if (orgForm.address_line2 && orgForm.address_line2.trim().length > 200) {
      errs.address_line2 = 'Address line 2 cannot exceed 200 characters';
    }

    if (orgForm.city && orgForm.city.trim()) {
      const c = orgForm.city.trim();
      if (c.length < 2) errs.city = 'City must be at least 2 characters';
      if (c.length > 100) errs.city = 'City cannot exceed 100 characters';
    }

    if (orgForm.state && orgForm.state.trim()) {
      const s = orgForm.state.trim();
      if (!INDIAN_STATES_AND_UTS.includes(s as any)) {
        errs.state = 'Please select a valid Indian State or Union Territory';
      }
    }

    if (orgForm.postal_code && orgForm.postal_code.trim()) {
      const pin = orgForm.postal_code.trim();
      const pinRegex = /^[1-9][0-9]{5}$/;
      if (!pinRegex.test(pin)) {
        errs.postal_code = 'PIN code must be exactly 6 digits and cannot start with 0';
      }
    }

    if (orgForm.website_url && orgForm.website_url.trim()) {
      const w = orgForm.website_url.trim();
      if (!/^https?:\/\/.+/i.test(w)) {
        errs.website_url = 'Website must start with http:// or https://';
      }
    }

    if (orgForm.tax_id && orgForm.tax_id.trim()) {
      const g = orgForm.tax_id.trim().toUpperCase();
      const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
      if (!gstinRegex.test(g)) {
        errs.tax_id = 'GSTIN must match standard Indian format (e.g. 29ABCDE1234F1Z5)';
      }
    }

    setOrgErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSaveDetails = async () => {
    if (!validateDetails()) return;
    setSavingDetails(true);
    try {
      const updated = await profileService.updateProfile({
        name: detailsForm.name.trim(),
        phone: detailsForm.phone.trim() || null,
      });
      setProfile(updated);
      updateUser({ name: updated.me.name });
      toast.success('Profile details updated successfully.');
      setIsEditingDetails(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to update profile.');
    } finally {
      setSavingDetails(false);
    }
  };

  const handleCancelDetails = () => {
    if (isEditingDetails && (detailsForm.name !== (profile?.me.name || '') || detailsForm.phone !== (profile?.me.phone || ''))) {
      if (!window.confirm('You have unsaved changes. Discard them?')) return;
    }
    setDetailsForm({
      name: profile?.me.name || '',
      phone: profile?.me.phone || '',
    });
    setDetailsErrors({});
    setIsEditingDetails(false);
  };

  const handleSaveOrg = async () => {
    if (!validateOrg()) return;
    setSavingOrg(true);
    try {
      const payload = {
        contact_person_name: orgForm.contact_person_name.trim() || null,
        phone_number: orgForm.phone_number.trim() || null,
        address_line1: orgForm.address_line1.trim() || null,
        address_line2: orgForm.address_line2.trim() || null,
        city: orgForm.city.trim() || null,
        state: orgForm.state.trim() || null,
        postal_code: orgForm.postal_code.trim() || null,
        website_url: orgForm.website_url.trim() || null,
        tax_id: orgForm.tax_id.trim().toUpperCase() || null,
      };
      const updated = await profileService.updateOrganization(payload);
      setProfile(updated);
      toast.success('Organization details updated successfully.');
      setIsEditingOrg(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to update organization details.');
    } finally {
      setSavingOrg(false);
    }
  };

  const handleCancelOrg = () => {
    if (profile?.role === 'smb_owner' && (profile as OwnerProfileData).organization) {
      const org = (profile as OwnerProfileData).organization!;
      setOrgForm({
        contact_person_name: org.contact_person || '',
        phone_number: org.phone || '',
        address_line1: org.address_line1 || '',
        address_line2: org.address_line2 || '',
        city: org.city || '',
        state: org.state || '',
        postal_code: org.pin_code || '',
        website_url: org.website || '',
        tax_id: org.gstin || '',
      });
    }
    setOrgErrors({});
    setIsEditingOrg(false);
  };

  const handleOpenEmailModal = () => {
    setEmailForm({ new_email: '', current_password: '' });
    setEmailErrors({});
    setShowEmailModal(true);
  };

  const handleCloseEmailModal = () => {
    setShowEmailModal(false);
    setEmailForm({ new_email: '', current_password: '' });
    setEmailErrors({});
  };

  const handleSaveEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs: { new_email?: string; current_password?: string; general?: string } = {};

    const trimmedEmail = emailForm.new_email.trim();
    if (!trimmedEmail) {
      errs.new_email = 'New email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errs.new_email = 'Please enter a valid email address';
    }

    if (!emailForm.current_password) {
      errs.current_password = 'Current password is required to verify identity';
    }

    if (Object.keys(errs).length > 0) {
      setEmailErrors(errs);
      return;
    }

    setSavingEmail(true);
    setEmailErrors({});

    try {
      const updated = await profileService.updateEmail({
        new_email: trimmedEmail,
        current_password: emailForm.current_password,
      });
      setProfile(updated);
      updateUser({ email: trimmedEmail });
      toast.success('Email address updated successfully.');
      handleCloseEmailModal();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 403) {
        setEmailErrors({ current_password: detail || 'Incorrect password.' });
      } else if (status === 409) {
        setEmailErrors({ new_email: detail || 'This email is already in use.' });
      } else {
        setEmailErrors({ general: typeof detail === 'string' ? detail : 'Failed to update email address.' });
      }
    } finally {
      setSavingEmail(false);
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'smb_owner':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <Building2 className="w-3.5 h-3.5" />
            <span>Organization Owner</span>
          </span>
        );
      case 'team_member':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <Users className="w-3.5 h-3.5" />
            <span>Operations Team Member</span>
          </span>
        );
      case 'admin':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <Shield className="w-3.5 h-3.5" />
            <span>Platform Administrator</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-helios-accent-blue/10 dark:bg-helios-accent-blue/20 flex items-center justify-center text-helios-accent-blue border border-helios-accent-blue/20">
            <User className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                {profile ? profile.me.name : 'User Profile'}
              </h1>
              {profile && getRoleBadge(profile.role)}
            </div>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-2">
              <Mail className="w-3.5 h-3.5 text-gray-400" />
              <span>{profile?.me.email || 'Account Credentials & Boundaries'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchProfile}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-helios-bg-light dark:hover:bg-helios-bg-dark transition shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/change-password')}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-sm"
          >
            <KeyRound className="w-4 h-4" />
            <span>Change Password</span>
          </button>
        </div>
      </div>

      {/* Loading Skeleton State */}
      {loading && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4">
            <LoadingSkeleton variant="text" width="20%" height="20px" />
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <LoadingSkeleton variant="card" count={4} />
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4">
            <LoadingSkeleton variant="text" width="25%" height="20px" />
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <LoadingSkeleton variant="card" count={3} />
            </div>
          </div>
        </div>
      )}

      {/* Error State with Retry Button */}
      {!loading && error && (
        <div className="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Failed to load profile data</p>
              <p className="text-xs text-rose-700/80 dark:text-rose-400/80">{error}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={fetchProfile}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 text-white hover:bg-rose-700 transition shrink-0 shadow-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Content Rendering By Role */}
      {!loading && profile && (
        <>
          {/* SECTION 1: My Details (Common to all roles) */}
          <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
            <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark pb-3">
              <div className="flex items-center gap-2">
                <IdCard className="w-4 h-4 text-helios-accent-blue" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  My Details
                </h2>
              </div>

              {!isEditingDetails ? (
                <button
                  type="button"
                  id="edit-my-details-btn"
                  onClick={() => setIsEditingDetails(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-helios-accent-blue/10 text-helios-accent-blue hover:bg-helios-accent-blue/20 transition"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Edit Details</span>
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCancelDetails}
                    disabled={savingDetails}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark hover:bg-black/5 dark:hover:bg-white/5 transition"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Cancel</span>
                  </button>
                  <button
                    type="button"
                    id="save-my-details-btn"
                    onClick={handleSaveDetails}
                    disabled={savingDetails}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-xs disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingDetails ? 'Saving...' : 'Save'}</span>
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {/* Full Name */}
              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Full Name
                </label>
                {!isEditingDetails ? (
                  <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {profile.me.name || 'Not provided'}
                  </span>
                ) : (
                  <div>
                    <input
                      type="text"
                      id="profile-name-input"
                      value={detailsForm.name}
                      onChange={(e) => setDetailsForm({ ...detailsForm, name: e.target.value })}
                      className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                      placeholder="Your full name"
                    />
                    {detailsErrors.name && (
                      <p className="text-[11px] text-rose-500 mt-1 font-medium">{detailsErrors.name}</p>
                    )}
                  </div>
                )}
              </div>

              {/* Email Address with Change Email Button */}
              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Email Address
                  </span>
                  <button
                    type="button"
                    id="open-change-email-btn"
                    onClick={handleOpenEmailModal}
                    className="text-[11px] font-semibold text-helios-accent-blue hover:underline"
                  >
                    Change email
                  </button>
                </div>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark break-all">
                  {profile.me.email || 'Not provided'}
                </span>
              </div>

              {/* Phone Number */}
              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Phone Number
                </label>
                {!isEditingDetails ? (
                  <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {profile.me.phone || 'Not provided'}
                  </span>
                ) : (
                  <div>
                    <input
                      type="text"
                      id="profile-phone-input"
                      value={detailsForm.phone}
                      onChange={(e) => setDetailsForm({ ...detailsForm, phone: e.target.value })}
                      className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                      placeholder="+91 9876543210"
                    />
                    {detailsErrors.phone && (
                      <p className="text-[11px] text-rose-500 mt-1 font-medium">{detailsErrors.phone}</p>
                    )}
                  </div>
                )}
              </div>

              {/* Last Login */}
              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Last Login
                </span>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {profile.me.last_login ? formatDateTimeIN(profile.me.last_login) : 'Not provided'}
                </span>
              </div>

              {/* Staff ID & Designation (Read-only, Managed by your admin) */}
              {profile.role === 'team_member' && (
                <>
                  <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        Staff ID
                      </span>
                      <span className="text-[10px] text-gray-400 italic">Managed by your admin</span>
                    </div>
                    <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      {(profile as TeamMemberProfileData).me.staff_id || 'Not provided'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        Designation
                      </span>
                      <span className="text-[10px] text-gray-400 italic">Managed by your admin</span>
                    </div>
                    <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      {(profile as TeamMemberProfileData).me.designation || 'Not provided'}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* ROLE 1: Organization Owner Sections */}
          {profile.role === 'smb_owner' && (
            <>
              {/* My Organization */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-helios-accent-blue" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      My Organization
                    </h2>
                  </div>

                  {(profile as OwnerProfileData).organization && (
                    !isEditingOrg ? (
                      <button
                        type="button"
                        id="edit-my-org-btn"
                        onClick={() => setIsEditingOrg(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-helios-accent-blue/10 text-helios-accent-blue hover:bg-helios-accent-blue/20 transition"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit Organization</span>
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handleCancelOrg}
                          disabled={savingOrg}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border border-helios-border-light dark:border-helios-border-dark hover:bg-black/5 dark:hover:bg-white/5 transition"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Cancel</span>
                        </button>
                        <button
                          type="button"
                          id="save-my-org-btn"
                          onClick={handleSaveOrg}
                          disabled={savingOrg}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-xs disabled:opacity-50"
                        >
                          <Save className="w-3.5 h-3.5" />
                          <span>{savingOrg ? 'Saving...' : 'Save'}</span>
                        </button>
                      </div>
                    )
                  )}
                </div>

                {(profile as OwnerProfileData).organization ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    {/* Business Name (Read-only, Managed by admin) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          Organization Name
                        </span>
                        <span className="text-[10px] text-gray-400 italic">Managed by your admin</span>
                      </div>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.business_name || 'Not provided'}
                      </span>
                    </div>

                    {/* Industry (Read-only, Managed by admin) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          Industry
                        </span>
                        <span className="text-[10px] text-gray-400 italic">Managed by your admin</span>
                      </div>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.industry || 'Not provided'}
                      </span>
                    </div>

                    {/* Contact Email (Read-only, Managed by admin) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          Contact Email
                        </span>
                        <span className="text-[10px] text-gray-400 italic">Managed by your admin</span>
                      </div>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark break-all">
                        {(profile as OwnerProfileData).organization?.contact_email || 'Not provided'}
                      </span>
                    </div>

                    {/* Contact Person Name (Editable) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Contact Person
                      </label>
                      {!isEditingOrg ? (
                        <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {(profile as OwnerProfileData).organization?.contact_person || 'Not provided'}
                        </span>
                      ) : (
                        <div>
                          <input
                            type="text"
                            id="org-contact-person-input"
                            value={orgForm.contact_person_name}
                            onChange={(e) => setOrgForm({ ...orgForm, contact_person_name: e.target.value })}
                            className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                            placeholder="Primary contact name"
                          />
                          {orgErrors.contact_person_name && (
                            <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.contact_person_name}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Contact Phone (Editable) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Organization Phone
                      </label>
                      {!isEditingOrg ? (
                        <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {(profile as OwnerProfileData).organization?.phone || 'Not provided'}
                        </span>
                      ) : (
                        <div>
                          <input
                            type="text"
                            id="org-phone-input"
                            value={orgForm.phone_number}
                            onChange={(e) => setOrgForm({ ...orgForm, phone_number: e.target.value })}
                            className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                            placeholder="+91 9876543210"
                          />
                          {orgErrors.phone_number && (
                            <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.phone_number}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* PIN Code (Editable) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        PIN Code
                      </label>
                      {!isEditingOrg ? (
                        <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {(profile as OwnerProfileData).organization?.pin_code || 'Not provided'}
                        </span>
                      ) : (
                        <div>
                          <input
                            type="text"
                            id="org-pincode-input"
                            value={orgForm.postal_code}
                            maxLength={6}
                            onChange={(e) => setOrgForm({ ...orgForm, postal_code: e.target.value })}
                            className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                            placeholder="6-digit PIN code"
                          />
                          {orgErrors.postal_code && (
                            <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.postal_code}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Address Line 1 (Editable) */}
                    {isEditingOrg && (
                      <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark sm:col-span-2">
                        <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                          Address Line 1
                        </label>
                        <input
                          type="text"
                          id="org-address1-input"
                          value={orgForm.address_line1}
                          onChange={(e) => setOrgForm({ ...orgForm, address_line1: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                          placeholder="Street address line 1"
                        />
                        {orgErrors.address_line1 && (
                          <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.address_line1}</p>
                        )}
                      </div>
                    )}

                    {/* Address Line 2 (Editable) */}
                    {isEditingOrg && (
                      <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                        <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                          Address Line 2 (Optional)
                        </label>
                        <input
                          type="text"
                          id="org-address2-input"
                          value={orgForm.address_line2}
                          onChange={(e) => setOrgForm({ ...orgForm, address_line2: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                          placeholder="Suite, unit, floor"
                        />
                        {orgErrors.address_line2 && (
                          <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.address_line2}</p>
                        )}
                      </div>
                    )}

                    {/* City (Editable) */}
                    {isEditingOrg && (
                      <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                        <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                          City
                        </label>
                        <input
                          type="text"
                          id="org-city-input"
                          value={orgForm.city}
                          onChange={(e) => setOrgForm({ ...orgForm, city: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                          placeholder="City"
                        />
                        {orgErrors.city && (
                          <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.city}</p>
                        )}
                      </div>
                    )}

                    {/* State (Editable) */}
                    {isEditingOrg && (
                      <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                        <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                          State / Union Territory
                        </label>
                        <select
                          id="org-state-select"
                          value={orgForm.state}
                          onChange={(e) => setOrgForm({ ...orgForm, state: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                        >
                          <option value="">Select State or UT</option>
                          {INDIAN_STATES_AND_UTS.map((st) => (
                            <option key={st} value={st}>
                              {st}
                            </option>
                          ))}
                        </select>
                        {orgErrors.state && (
                          <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.state}</p>
                        )}
                      </div>
                    )}

                    {/* Read-only Full Address (when not editing) */}
                    {!isEditingOrg && (
                      <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark sm:col-span-2">
                        <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                          Full Address
                        </span>
                        <span className="text-sm font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-start gap-1.5">
                          <MapPin className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                          <span>{(profile as OwnerProfileData).organization?.full_address || 'Not provided'}</span>
                        </span>
                      </div>
                    )}

                    {/* GSTIN / Tax ID (Editable) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        GSTIN / Tax ID
                      </label>
                      {!isEditingOrg ? (
                        <span className="text-sm font-bold font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                          {(profile as OwnerProfileData).organization?.gstin || 'Not provided'}
                        </span>
                      ) : (
                        <div>
                          <input
                            type="text"
                            id="org-gstin-input"
                            value={orgForm.tax_id}
                            maxLength={15}
                            onChange={(e) => setOrgForm({ ...orgForm, tax_id: e.target.value.toUpperCase() })}
                            className="w-full px-3 py-1.5 text-xs font-mono font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue uppercase"
                            placeholder="29ABCDE1234F1Z5"
                          />
                          {orgErrors.tax_id && (
                            <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.tax_id}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Website (Editable) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <label className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Website
                      </label>
                      {!isEditingOrg ? (
                        (profile as OwnerProfileData).organization?.website ? (
                          <a
                            href={(profile as OwnerProfileData).organization!.website!}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-bold text-helios-accent-blue hover:underline flex items-center gap-1.5"
                          >
                            <Globe className="w-3.5 h-3.5" />
                            <span>{(profile as OwnerProfileData).organization!.website}</span>
                          </a>
                        ) : (
                          <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                            Not provided
                          </span>
                        )
                      ) : (
                        <div>
                          <input
                            type="text"
                            id="org-website-input"
                            value={orgForm.website_url}
                            onChange={(e) => setOrgForm({ ...orgForm, website_url: e.target.value })}
                            className="w-full px-3 py-1.5 text-xs font-medium rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                            placeholder="https://example.com"
                          />
                          {orgErrors.website_url && (
                            <p className="text-[11px] text-rose-500 mt-1 font-medium">{orgErrors.website_url}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Registration Date (Read-only) */}
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Registration Date
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        <span>
                          {(profile as OwnerProfileData).organization?.created_date
                            ? formatDateIN((profile as OwnerProfileData).organization!.created_date!)
                            : 'Not provided'}
                        </span>
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <Building className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm font-medium">Organization details not provided.</p>
                  </div>
                )}
              </div>

              {/* My Helios Team */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center gap-2 border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <Users className="w-4 h-4 text-helios-accent-blue" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    My Helios Team
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Assigned Team Member Card */}
                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        Assigned Operations Specialist
                      </span>
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    </div>

                    {(profile as OwnerProfileData).assigned_team_member ? (
                      <div className="space-y-2">
                        <div>
                          <p className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                            {(profile as OwnerProfileData).assigned_team_member!.name}
                          </p>
                          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-1.5 mt-0.5">
                            <Briefcase className="w-3.5 h-3.5 text-gray-400" />
                            <span>
                              {(profile as OwnerProfileData).assigned_team_member!.designation ||
                                'Operations Specialist'}
                            </span>
                          </p>
                        </div>

                        <div className="pt-2 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
                          <a
                            href={`mailto:${(profile as OwnerProfileData).assigned_team_member!.email}`}
                            className="inline-flex items-center gap-2 text-helios-accent-blue hover:underline font-medium"
                          >
                            <Mail className="w-3.5 h-3.5" />
                            <span>{(profile as OwnerProfileData).assigned_team_member!.email}</span>
                          </a>
                          <div>
                            {(profile as OwnerProfileData).assigned_team_member!.phone ? (
                              <a
                                href={`tel:${(profile as OwnerProfileData).assigned_team_member!.phone}`}
                                className="inline-flex items-center gap-2 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:text-helios-accent-blue font-medium"
                              >
                                <Phone className="w-3.5 h-3.5 text-gray-400" />
                                <span>{(profile as OwnerProfileData).assigned_team_member!.phone}</span>
                              </a>
                            ) : (
                              <span className="inline-flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                                <Phone className="w-3.5 h-3.5 text-gray-400" />
                                <span>Phone: Not provided</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="py-4 text-center text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        <p className="font-medium">No dedicated team member currently assigned.</p>
                        <p className="text-[11px] text-gray-400 mt-1">Not provided</p>
                      </div>
                    )}
                  </div>

                  {/* Admin Contact Card */}
                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                        Helios Administrator
                      </span>
                      <Shield className="w-3.5 h-3.5 text-purple-500" />
                    </div>

                    {(profile as OwnerProfileData).admin_contact ? (
                      <div className="space-y-2">
                        <div>
                          <p className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                            {(profile as OwnerProfileData).admin_contact!.name}
                          </p>
                          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-1.5 mt-0.5">
                            <Shield className="w-3.5 h-3.5 text-gray-400" />
                            <span>Platform Escalations & Administration</span>
                          </p>
                        </div>

                        <div className="pt-2 border-t border-helios-border-light dark:border-helios-border-dark space-y-1.5 text-xs">
                          <a
                            href={`mailto:${(profile as OwnerProfileData).admin_contact!.email}`}
                            className="inline-flex items-center gap-2 text-helios-accent-blue hover:underline font-medium"
                          >
                            <Mail className="w-3.5 h-3.5" />
                            <span>{(profile as OwnerProfileData).admin_contact!.email}</span>
                          </a>
                          <div>
                            {(profile as OwnerProfileData).admin_contact!.phone ? (
                              <a
                                href={`tel:${(profile as OwnerProfileData).admin_contact!.phone}`}
                                className="inline-flex items-center gap-2 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:text-helios-accent-blue font-medium"
                              >
                                <Phone className="w-3.5 h-3.5 text-gray-400" />
                                <span>{(profile as OwnerProfileData).admin_contact!.phone}</span>
                              </a>
                            ) : (
                              <span className="inline-flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                                <Phone className="w-3.5 h-3.5 text-gray-400" />
                                <span>Phone: Not provided</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="py-4 text-center text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        <p className="font-medium">Admin contact not provided.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ROLE 2: Team Member Sections */}
          {profile.role === 'team_member' && (
            <>
              {/* My Organizations */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-light pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-helios-accent-blue" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      My Organizations
                    </h2>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400">
                    {(profile as TeamMemberProfileData).assigned_organizations.length} Assigned
                  </span>
                </div>

                {(profile as TeamMemberProfileData).assigned_organizations.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(profile as TeamMemberProfileData).assigned_organizations.map((org) => (
                      <div
                        key={org.tenant_id}
                        className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                              {org.business_name}
                            </h3>
                            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
                              {org.industry || 'Not provided'} ·{' '}
                              {[org.city, org.state].filter(Boolean).join(', ') || 'Not provided'}
                            </p>
                          </div>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-gray-500">
                            Org #{org.tenant_id}
                          </span>
                        </div>

                        <div className="pt-2 border-t border-helios-border-light dark:border-helios-border-dark grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                              Organization Owner
                            </span>
                            <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                              {org.owner_name || org.contact_person || 'Not provided'}
                            </span>
                          </div>

                          <div>
                            <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                              Last Data Date
                            </span>
                            <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-1">
                              <Clock className="w-3 h-3 text-gray-400" />
                              <span>{org.last_data_date ? formatDateIN(org.last_data_date) : 'Not provided'}</span>
                            </span>
                          </div>

                          <div className="col-span-2 pt-1 flex flex-wrap items-center gap-3 text-xs">
                            {org.owner_email ? (
                              <a
                                href={`mailto:${org.owner_email}`}
                                className="inline-flex items-center gap-1.5 text-helios-accent-blue hover:underline"
                              >
                                <Mail className="w-3 h-3" />
                                <span>{org.owner_email}</span>
                              </a>
                            ) : (
                              <span className="text-gray-400">Email: Not provided</span>
                            )}

                            {org.owner_phone ? (
                              <a
                                href={`tel:${org.owner_phone}`}
                                className="inline-flex items-center gap-1.5 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:text-helios-accent-blue"
                              >
                                <Phone className="w-3 h-3 text-gray-400" />
                                <span>{org.owner_phone}</span>
                              </a>
                            ) : (
                              <span className="text-gray-400">Phone: Not provided</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                    <Building2 className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm font-medium">No organizations assigned to your profile yet.</p>
                    <p className="text-xs text-gray-400 mt-1">Not provided</p>
                  </div>
                )}
              </div>

              {/* Admin Contact for Team Member */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center gap-2 border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <Shield className="w-4 h-4 text-purple-500" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Admin Contact
                  </h2>
                </div>

                {(profile as TeamMemberProfileData).admin_contact ? (
                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark max-w-md space-y-2">
                    <p className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      {(profile as TeamMemberProfileData).admin_contact!.name}
                    </p>
                    <div className="space-y-1.5 text-xs">
                      <div>
                        <a
                          href={`mailto:${(profile as TeamMemberProfileData).admin_contact!.email}`}
                          className="inline-flex items-center gap-2 text-helios-accent-blue hover:underline font-medium"
                        >
                          <Mail className="w-3.5 h-3.5" />
                          <span>{(profile as TeamMemberProfileData).admin_contact!.email}</span>
                        </a>
                      </div>
                      <div>
                        {(profile as TeamMemberProfileData).admin_contact!.phone ? (
                          <a
                            href={`tel:${(profile as TeamMemberProfileData).admin_contact!.phone}`}
                            className="inline-flex items-center gap-2 text-helios-text-primary-light dark:text-helios-text-primary-dark hover:text-helios-accent-blue font-medium"
                          >
                            <Phone className="w-3.5 h-3.5 text-gray-400" />
                            <span>{(profile as TeamMemberProfileData).admin_contact!.phone}</span>
                          </a>
                        ) : (
                          <span className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center gap-1.5">
                            <Phone className="w-3.5 h-3.5 text-gray-400" />
                            <span>Phone: Not provided</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    Not provided
                  </div>
                )}
              </div>
            </>
          )}

          {/* ROLE 3: Admin Sections */}
          {profile.role === 'admin' && (
            <>
              {/* Platform Summary */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center gap-2 border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <Activity className="w-4 h-4 text-helios-accent-blue" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Platform Summary
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-helios-accent-blue">
                      <Building2 className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block">
                        Active Organizations
                      </span>
                      <span className="text-2xl font-black text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatCountIN((profile as AdminProfileData).platform_summary.active_organizations)}
                      </span>
                    </div>
                  </div>

                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                      <UserCheck className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block">
                        Active Organization Owners
                      </span>
                      <span className="text-2xl font-black text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatCountIN((profile as AdminProfileData).platform_summary.active_owners)}
                      </span>
                    </div>
                  </div>

                  <div className="p-5 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-600 dark:text-purple-400">
                      <Users className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block">
                        Active Team Members
                      </span>
                      <span className="text-2xl font-black text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {formatCountIN((profile as AdminProfileData).platform_summary.active_team_members)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Team Members List */}
              <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs space-y-4 transition-colors">
                <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-helios-accent-blue" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      Team Members List
                    </h2>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400">
                    {(profile as AdminProfileData).team_members.length} Total
                  </span>
                </div>

                {(profile as AdminProfileData).team_members.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-semibold">
                          <th className="py-3 px-4">Name</th>
                          <th className="py-3 px-4">Designation</th>
                          <th className="py-3 px-4">Email</th>
                          <th className="py-3 px-4">Phone</th>
                          <th className="py-3 px-4 text-right">Assigned Organizations</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                        {(profile as AdminProfileData).team_members.map((tm) => (
                          <tr
                            key={tm.user_id}
                            className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                          >
                            <td className="py-3 px-4 font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                              {tm.name}
                            </td>
                            <td className="py-3 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                              {tm.designation || 'Not provided'}
                            </td>
                            <td className="py-3 px-4">
                              <a
                                href={`mailto:${tm.email}`}
                                className="text-helios-accent-blue hover:underline font-medium"
                              >
                                {tm.email}
                              </a>
                            </td>
                            <td className="py-3 px-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                              {tm.phone ? (
                                <a
                                  href={`tel:${tm.phone}`}
                                  className="text-helios-text-primary-light dark:text-helios-text-primary-dark hover:underline"
                                >
                                  {tm.phone}
                                </a>
                              ) : (
                                'Not provided'
                              )}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-helios-accent-blue">
                                {formatCountIN(tm.assigned_organizations_count)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <Users className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm font-medium">No team members registered.</p>
                    <p className="text-xs text-gray-400 mt-1">Not provided</p>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}

      {/* Change Email Dialog Modal */}
      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-helios-border-light dark:border-helios-border-dark">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-helios-accent-blue/15 flex items-center justify-center text-helios-accent-blue">
                  <Mail className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Change Email Address
                </h3>
              </div>
              <button
                type="button"
                onClick={handleCloseEmailModal}
                disabled={savingEmail}
                className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark p-1 rounded-lg transition-colors"
                aria-label="Close dialog"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {emailErrors.general && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{emailErrors.general}</span>
              </div>
            )}

            <form onSubmit={handleSaveEmail} className="space-y-4 text-xs" noValidate>
              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  New Email Address
                </label>
                <input
                  type="email"
                  id="new-email-input"
                  value={emailForm.new_email}
                  onChange={(e) => setEmailForm({ ...emailForm, new_email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl text-xs bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                  placeholder="name@company.com"
                  autoComplete="email"
                />
                {emailErrors.new_email && (
                  <p className="text-[11px] text-rose-500 mt-1 font-medium flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    <span>{emailErrors.new_email}</span>
                  </p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="current-password-input"
                    value={emailForm.current_password}
                    onChange={(e) => setEmailForm({ ...emailForm, current_password: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl text-xs bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
                    placeholder="Enter your current password"
                    autoComplete="current-password"
                  />
                  <Lock className="w-3.5 h-3.5 text-gray-400 absolute right-3 top-2.5 pointer-events-none" />
                </div>
                {emailErrors.current_password && (
                  <p className="text-[11px] text-rose-500 mt-1 font-medium flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    <span>{emailErrors.current_password}</span>
                  </p>
                )}
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-helios-border-light dark:border-helios-border-dark">
                <button
                  type="button"
                  onClick={handleCloseEmailModal}
                  disabled={savingEmail}
                  className="px-3.5 py-1.5 rounded-xl border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:bg-black/5 dark:hover:bg-white/5 transition font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="confirm-change-email-btn"
                  disabled={savingEmail}
                  className="px-4 py-1.5 rounded-xl bg-helios-accent-blue text-white font-bold hover:bg-blue-600 transition shadow-xs disabled:opacity-50 flex items-center gap-1.5"
                >
                  {savingEmail ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Updating...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Update Email</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
