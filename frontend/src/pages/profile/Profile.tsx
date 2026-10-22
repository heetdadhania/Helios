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
} from 'lucide-react';
import { profileService } from '@/services/profileService';
import {
  ProfileData,
  OwnerProfileData,
  TeamMemberProfileData,
  AdminProfileData,
} from '@/types/profile';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { formatDateIN, formatDateTimeIN, formatCountIN } from '@/utils/currency';

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await profileService.getProfile();
      setProfile(data);
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
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Full Name
                </span>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {profile.me.name || 'Not provided'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Email Address
                </span>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark break-all">
                  {profile.me.email || 'Not provided'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Phone Number
                </span>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {profile.me.phone || 'Not provided'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                  Last Login
                </span>
                <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {profile.me.last_login ? formatDateTimeIN(profile.me.last_login) : 'Not provided'}
                </span>
              </div>

              {profile.role === 'team_member' && (
                <>
                  <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                    <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                      Staff ID
                    </span>
                    <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                      {(profile as TeamMemberProfileData).me.staff_id || 'Not provided'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                    <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                      Designation
                    </span>
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
                <div className="flex items-center gap-2 border-b border-helios-border-light dark:border-helios-border-dark pb-3">
                  <Building2 className="w-4 h-4 text-helios-accent-blue" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    My Organization
                  </h2>
                </div>

                {(profile as OwnerProfileData).organization ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Business Name
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.business_name || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Industry
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.industry || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Contact Person
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.contact_person || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Contact Email
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark break-all">
                        {(profile as OwnerProfileData).organization?.contact_email || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Phone Number
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.phone || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        PIN Code
                      </span>
                      <span className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.pin_code || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark sm:col-span-2">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Full Address
                      </span>
                      <span className="text-sm font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-start gap-1.5">
                        <MapPin className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                        <span>{(profile as OwnerProfileData).organization?.full_address || 'Not provided'}</span>
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        GSTIN / Tax ID
                      </span>
                      <span className="text-sm font-bold font-mono text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        {(profile as OwnerProfileData).organization?.gstin || 'Not provided'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark">
                      <span className="text-[11px] font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark block mb-1">
                        Website
                      </span>
                      {(profile as OwnerProfileData).organization?.website ? (
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
                      )}
                    </div>

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
                <div className="flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark pb-3">
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
    </div>
  );
};

export default Profile;
