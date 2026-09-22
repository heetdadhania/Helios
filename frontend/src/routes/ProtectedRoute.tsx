import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types/auth';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles }) => {
  const { isAuthenticated, isLoading, user, role } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-helios-bg-light dark:bg-helios-bg-dark">
        <div className="w-8 h-8 rounded-full border-2 border-helios-accent-blue border-t-transparent animate-spin mb-3" />
        <span className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          Validating session...
        </span>
      </div>
    );
  }

  // If not authenticated, send to login and preserve intended destination
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If role is not authorized for this specific route group, redirect to authorized portal
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    const defaultTarget = role === 'smb_owner' ? '/client/dashboard' : '/admin/uploads';
    return <Navigate to={defaultTarget} replace />;
  }

  return <Outlet />;
};
