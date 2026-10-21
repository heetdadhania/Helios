import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Lock, Mail, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
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
    setErrorMsg(null);
    try {
      await login(data);
      // Route appropriately based on email role convention
      if (data.email.includes('admin') || data.email.includes('team')) {
        navigate('/admin/home');
      } else {
        navigate('/client/home');
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    }
  };

  const setDemoRole = (email: string, password: string) => {
    setErrorMsg(null);
    setValue('email', email, { shouldValidate: true });
    setValue('password', password, { shouldValidate: true });
  };

  return (
    <div className="w-full max-w-sm mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Login
        </h2>
        <p className="mt-1 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          Enter your authorized organizational credentials.
        </p>
      </div>

      {errorMsg && (
        <div className="mb-4 p-3 rounded-control bg-red-500/10 border border-red-500/20 text-helios-error text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Email Field */}
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
                alert('Contact your Helios organization administrator to reset your password.');
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

      {/* Helper text below - no public sign up link */}
      <div className="mt-6 pt-4 border-t border-helios-border-light dark:border-helios-border-dark text-center">
        <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          Accounts are provisioned by organizational administrators only.
        </p>

        {/* Quick Demo Pre-fill Links for Testing */}
        <div className="mt-3 flex items-center justify-center gap-2">
          <span className="text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            Demo quick-fill:
          </span>
          <button
            type="button"
            onClick={() => setDemoRole('smb-owner-1@helios-test.dev', import.meta.env.VITE_TEST_ACCOUNT_PASSWORD || '')}
            className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-helios-accent-teal hover:underline font-mono"
          >
            Client
          </button>
          <button
            type="button"
            onClick={() => setDemoRole('team-member-1@helios-test.dev', import.meta.env.VITE_TEST_ACCOUNT_PASSWORD || '')}
            className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-purple-400 hover:underline font-mono"
          >
            Team
          </button>
          <button
            type="button"
            onClick={() => setDemoRole('admin@helios.io', import.meta.env.VITE_ADMIN_PASSWORD || '')}
            className="text-[10px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5 text-helios-accent-blue hover:underline font-mono"
          >
            Admin
          </button>
        </div>
      </div>
    </div>
  );
};
