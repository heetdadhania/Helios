import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Lock, Mail, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { HeliosLogo } from '@/components/HeliosLogo';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LoginCredentials } from '@/types/auth';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid business email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: true,
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setErrorMessage(null);
    try {
      const user = await login(data as LoginCredentials);
      
      // If user must change password, immediately navigate to /change-password
      if (user.must_change_password) {
        navigate('/change-password', { replace: true });
        return;
      }

      // Role-based redirect:
      // smb_owner -> /client/home
      // team_member or admin -> /admin/home
      const from = (location.state as any)?.from?.pathname;
      if (from && from !== '/login') {
        navigate(from, { replace: true });
      } else if (user.role === 'smb_owner') {
        navigate('/client/home', { replace: true });
      } else {
        navigate('/admin/home', { replace: true });
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message;
      setErrorMessage(detail || 'Invalid email or password. Please verify your credentials.');
    }
  };

  const handleDemoFill = (email: string, password: string) => {
    setErrorMessage(null);
    setValue('email', email, { shouldValidate: true });
    setValue('password', password, { shouldValidate: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200 relative">
      {/* Top right theme toggle */}
      <div className="absolute top-5 right-5">
        <ThemeToggle />
      </div>

      {/* Main Split-Screen Floating Card */}
      <div className="w-full max-w-4xl min-h-[580px] rounded-card overflow-hidden shadow-soft border border-helios-border-light dark:border-helios-border-dark flex flex-col md:flex-row bg-helios-card-light dark:bg-helios-card-dark transition-colors">
        
        {/* Left Branding Panel (~50% width, gradient background with blue accent, rounded outer edge) */}
        <div className="relative md:w-1/2 p-8 lg:p-10 flex flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-900 text-white rounded-t-card md:rounded-tr-none md:rounded-l-card">
          <div className="relative z-10">
            {/* Helios Wordmark & Sunburst Logo top-left */}
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/15">
              <HeliosLogo size={24} showWordmark={true} className="text-white brightness-125" />
            </div>

            <div className="mt-8">
              <span className="text-xs font-semibold tracking-wider uppercase text-blue-200">
                Multi-Organization Data Platform
              </span>
              <h2 className="mt-2 text-2xl lg:text-3xl font-extrabold tracking-tight leading-tight">
                Designed for high-growth e-commerce teams.
              </h2>
              <p className="mt-3 text-sm text-blue-100/80 leading-relaxed">
                Connect your operational stores, automate Delta Lake pipelines, and synchronize enterprise telemetry in real time.
              </p>
            </div>
          </div>

          {/* Stylized / blurred preview of the dashboard peeking up from the bottom */}
          <div className="relative z-0 mt-6 -mb-12 -mr-10 opacity-90 transition-transform duration-500 hover:scale-[1.02]">
            <div className="w-[120%] p-4 rounded-card bg-helios-card-dark/80 backdrop-blur-md border border-white/20 shadow-2xl space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  <span className="text-[10px] font-mono text-blue-200 ml-2">sales_sync_daily.delta</span>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">
                  LIVE 99.98%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-white/5 border border-white/10">
                  <div className="text-[10px] text-blue-200">Monthly Revenue</div>
                  <div className="text-sm font-bold text-white mt-0.5">₹1,48,290</div>
                </div>
                <div className="p-2.5 rounded bg-white/5 border border-white/10">
                  <div className="text-[10px] text-blue-200">Delta Latency</div>
                  <div className="text-sm font-bold text-emerald-300 mt-0.5">138ms</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Form Panel (~50% width, background matches current theme) */}
        <div className="md:w-1/2 p-8 lg:p-10 flex flex-col justify-center bg-helios-card-light dark:bg-helios-card-dark transition-colors">
          <div className="w-full max-w-sm mx-auto">
            <div className="mb-6">
              <h2 className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Login
              </h2>
              <p className="mt-1 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Enter your authorized organizational credentials.
              </p>
            </div>

            {errorMessage && (
              <div className="mb-4 p-3 rounded-control bg-red-500/10 border border-red-500/20 text-helios-error text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Email Address */}
              <div>
                <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                  <input
                    type="email"
                    placeholder="name@company.com"
                    {...register('email')}
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-[11px] text-helios-error">{errors.email.message}</p>
                )}
              </div>

              {/* Password Field with inline Forgot password */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    Password
                  </label>
                  <a
                    href="#forgot-password"
                    onClick={(e) => {
                      e.preventDefault();
                      alert('Please contact your Helios administrator to reset your password.');
                    }}
                    className="text-[11px] font-medium text-helios-accent-blue hover:underline"
                  >
                    Forgot password?
                  </a>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    {...register('password')}
                    className="w-full pl-9 pr-10 py-2 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue rounded transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1 text-[11px] text-helios-error">{errors.password.message}</p>
                )}
              </div>

              {/* Remember me checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  id="rememberMe"
                  type="checkbox"
                  {...register('rememberMe')}
                  className="w-4 h-4 rounded text-helios-accent-blue focus:ring-helios-accent-blue border-helios-border-light dark:border-helios-border-dark bg-helios-bg-light dark:bg-helios-bg-dark"
                />
                <label
                  htmlFor="rememberMe"
                  className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark select-none"
                >
                  Remember me
                </label>
              </div>

              {/* Full-width primary-accent-colored Login button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 rounded-control bg-helios-accent-blue hover:bg-blue-600 active:bg-blue-700 text-white font-semibold text-xs tracking-wide transition-all duration-150 flex items-center justify-center gap-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-helios-accent-blue/50 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <span>Sign In to Helios</span>
                )}
              </button>
            </form>

            {/* Helper text below - NO public sign up link */}
            <div className="mt-6 pt-4 border-t border-helios-border-light dark:border-helios-border-dark text-center">
              <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                Accounts are provisioned by organizational administrators only.
              </p>

              {/* Demo quick-fill links for rapid testing */}
              <div className="mt-3 flex items-center justify-center gap-1.5">
                <span className="text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                  Quick-fill:
                </span>
                <button
                  type="button"
                  onClick={() => handleDemoFill('smb-owner-1@helios-test.dev', import.meta.env.VITE_TEST_ACCOUNT_PASSWORD || '')}
                  className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-helios-accent-teal hover:underline font-mono"
                >
                  Organization Owner
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoFill('team-member-1@helios-test.dev', import.meta.env.VITE_TEST_ACCOUNT_PASSWORD || '')}
                  className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-purple-400 hover:underline font-mono"
                >
                  Team
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoFill('admin@helios.io', import.meta.env.VITE_ADMIN_PASSWORD || '')}
                  className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-helios-accent-blue hover:underline font-mono"
                >
                  Admin
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
