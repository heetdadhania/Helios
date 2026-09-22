import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ClientLayout } from '@/layouts/ClientLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';

// Pages
import { Login } from '@/pages/Login';
import { DashboardPage } from '@/pages/client/DashboardPage';
import { UploadDataPage } from '@/pages/client/UploadDataPage';
import { ExportDataPage } from '@/pages/client/ExportDataPage';
import { PendingUploadsPage } from '@/pages/admin/PendingUploadsPage';
import { PipelineHealthPage } from '@/pages/admin/PipelineHealthPage';
import { DataQualityPage } from '@/pages/admin/DataQualityPage';
import { TenantsPage } from '@/pages/admin/TenantsPage';
import { TeamPage } from '@/pages/admin/TeamPage';
import { useAuth } from '@/hooks/useAuth';

const RootRedirect: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  return user.role === 'smb_owner' ? (
    <Navigate to="/client/dashboard" replace />
  ) : (
    <Navigate to="/admin/uploads" replace />
  );
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Root Redirection */}
      <Route path="/" element={<RootRedirect />} />

      {/* Public Login Route */}
      <Route path="/login" element={<Login />} />

      {/* Client Portal Route Group (SMB Owners & Admins) */}
      <Route element={<ProtectedRoute allowedRoles={['smb_owner', 'admin']} />}>
        <Route path="/client" element={<ClientLayout />}>
          <Route index element={<Navigate to="/client/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="upload" element={<UploadDataPage />} />
          <Route path="export" element={<ExportDataPage />} />
        </Route>
      </Route>

      {/* Admin Portal Route Group (Team Members & Admins) */}
      <Route element={<ProtectedRoute allowedRoles={['team_member', 'admin']} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/uploads" replace />} />
          <Route path="uploads" element={<PendingUploadsPage />} />
          <Route path="pending-uploads" element={<PendingUploadsPage />} />
          <Route path="pipeline-health" element={<PipelineHealthPage />} />
          <Route path="data-quality" element={<DataQualityPage />} />
          <Route path="tenants" element={<TenantsPage />} />
          <Route path="team" element={<TeamPage />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};
