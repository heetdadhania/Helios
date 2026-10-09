import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  LogOut,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/authService';
import { HeliosLogo } from '@/components/HeliosLogo';
import { ThemeToggle } from '@/components/ThemeToggle';

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required.'),
    new_password: z
      .string()
      .min(10, 'New password must be at least 10 characters long.'),
    confirm_password: z.string().min(1, 'Please confirm your new password.'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'New passwords do not match.',
    path: ['confirm_password'],
  })
  .refine((data) => data.current_password !== data.new_password, {
    message: 'New password must be different from current password.',
    path: ['new_password'],
  });

type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;

export const ChangePassword: React.FC = () => {
  const { user, updateUser, logout } = useAuth();
  const navigate = useNavigate();

  const [showCurrent, setShowCurrent] = useState<boolean>(false);
  const [showNew, setShowNew] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const onSubmit = async (values: ChangePasswordFormValues) => {
    setServerError(null);
    try {
      await authService.changePassword(values.current_password, values.new_password);
      updateUser({ must_change_password: false });
      setIsSuccess(true);

      // Redirect user to their landing page after brief acknowledgment
      setTimeout(() => {
        if (user?.role === 'smb_owner') {
          navigate('/client/dashboard', { replace: true });
        } else {
          navigate('/admin/uploads', { replace: true });
        }
      }, 1200);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setServerError(detail || 'Failed to update password. Please verify your current password.');
    }
  };

  const handleSignOut = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200 relative">
      {/* Top right theme toggle */}
      <div className="absolute top-5 right-5">
        <ThemeToggle />
      </div>

      {/* Main Split-Screen Floating Card */}
      <div className="w-full max-w-4xl min-h-[560px] rounded-card overflow-hidden shadow-soft border border-helios-border-light dark:border-helios-border-dark flex flex-col md:flex-row bg-helios-card-light dark:bg-helios-card-dark transition-colors">
        
        {/* Left Branding Panel */}
        <div className="relative md:w-1/2 p-8 lg:p-10 flex flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-900 text-white rounded-t-card md:rounded-tr-none md:rounded-l-card">
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/15">
              <HeliosLogo size={24} showWordmark={true} className="text-white brightness-125" />
            </div>

            <div className="mt-8">
              <span className="text-xs font-semibold tracking-wider uppercase text-blue-200">
                Security Requirement
              </span>
              <h2 className="mt-2 text-2xl lg:text-3xl font-extrabold tracking-tight leading-tight">
                First-Login Password Reset
              </h2>
              <p className="mt-3 text-sm text-blue-100/80 leading-relaxed">
                Your account was provisioned with a temporary administrative password.
                Please choose a permanent, confidential password before accessing the platform.
              </p>
            </div>
          </div>

          <div className="relative z-10 mt-6 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 space-y-2 text-xs text-blue-100">
            <div className="flex items-center gap-2 font-semibold text-white">
              <ShieldAlert className="w-4 h-4 text-amber-300" />
              <span>Password Security Rules</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-blue-100/80 text-[11px]">
              <li>Must be at least 10 characters in length</li>
              <li>Must differ from your temporary password</li>
              <li>Cannot navigate to any other screen until completed</li>
            </ul>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="md:w-1/2 p-8 lg:p-10 flex flex-col justify-center bg-helios-card-light dark:bg-helios-card-dark transition-colors">
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 mb-3">
                <KeyRound className="w-3.5 h-3.5" />
                <span>Password Change Required</span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Set Permanent Password
              </h1>
              <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                Authenticated as <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{user?.email}</span>
              </p>
            </div>

            {/* Server Error Message */}
            {serverError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{serverError}</span>
              </div>
            )}

            {/* Success Notification */}
            {isSuccess && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span className="font-semibold">Password updated successfully! Redirecting...</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Current Password Field */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Current / Temporary Password <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    placeholder="Enter current password"
                    {...register('current_password')}
                    disabled={isSubmitting || isSuccess}
                    className={`w-full px-3.5 py-2.5 pr-10 text-xs rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all ${
                      errors.current_password
                        ? 'border-rose-500 focus:ring-rose-500'
                        : 'border-helios-border-light dark:border-helios-border-dark'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrent(!showCurrent)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.current_password && (
                  <p className="text-[11px] text-rose-500 font-medium">
                    {errors.current_password.message}
                  </p>
                )}
              </div>

              {/* New Password Field */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  New Password <span className="text-rose-500">*</span> (min 10 characters)
                </label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    placeholder="Create a strong password"
                    {...register('new_password')}
                    disabled={isSubmitting || isSuccess}
                    className={`w-full px-3.5 py-2.5 pr-10 text-xs rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all ${
                      errors.new_password
                        ? 'border-rose-500 focus:ring-rose-500'
                        : 'border-helios-border-light dark:border-helios-border-dark'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew(!showNew)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.new_password && (
                  <p className="text-[11px] text-rose-500 font-medium">
                    {errors.new_password.message}
                  </p>
                )}
              </div>

              {/* Confirm New Password Field */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Confirm New Password <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    placeholder="Repeat new password"
                    {...register('confirm_password')}
                    disabled={isSubmitting || isSuccess}
                    className={`w-full px-3.5 py-2.5 pr-10 text-xs rounded-xl bg-black/5 dark:bg-white/5 border text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all ${
                      errors.confirm_password
                        ? 'border-rose-500 focus:ring-rose-500'
                        : 'border-helios-border-light dark:border-helios-border-dark'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.confirm_password && (
                  <p className="text-[11px] text-rose-500 font-medium">
                    {errors.confirm_password.message}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || isSuccess}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold bg-helios-accent-blue hover:bg-blue-600 text-white transition-all shadow-sm disabled:opacity-50 mt-2"
              >
                {isSubmitting ? (
                  <span>Updating Password...</span>
                ) : (
                  <>
                    <span>Confirm & Continue</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Sign Out link */}
            <div className="pt-2 border-t border-helios-border-light dark:border-helios-border-dark flex justify-between items-center text-xs">
              <span className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Need to use another account?
              </span>
              <button
                type="button"
                onClick={handleSignOut}
                className="inline-flex items-center gap-1 font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-rose-500 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
