import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ClientLayout } from '@/layouts/ClientLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';

// Pages
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/client/Dashboard';
import { DataSourceSelect } from '@/pages/client/DataSourceSelect';
import { UploadDataPage } from '@/pages/client/UploadDataPage';
import { ConnectDatabase } from '@/pages/client/ConnectDatabase';
import { ApiAccess } from '@/pages/client/ApiAccess';
import { ExportDataPage } from '@/pages/client/ExportDataPage';
import { PendingUploads } from '@/pages/admin/PendingUploads';
import { ConfirmSchema } from '@/pages/admin/ConfirmSchema';
import { PipelineHealth } from '@/pages/admin/PipelineHealth';
import { DataQualityLog } from '@/pages/admin/DataQualityLog';
import { Tenants } from '@/pages/admin/Tenants';
import { TeamMembers } from '@/pages/admin/TeamMembers';
import { useAuth } from '@/hooks/useAuth';

const RootRedirect: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  return user.role === 'smb_owner' ? (
    <Navigate to="/client/select-source" replace />
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
          <Route index element={<Navigate to="/client/select-source" replace />} />
          <Route path="select-source" element={<DataSourceSelect />} />
          <Route path="data-sources" element={<DataSourceSelect />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<UploadDataPage />} />
          <Route path="connect-db" element={<ConnectDatabase />} />
          <Route path="connect-database" element={<ConnectDatabase />} />
          <Route path="api-access" element={<ApiAccess />} />
          <Route path="api-keys" element={<ApiAccess />} />
          <Route path="export" element={<ExportDataPage />} />
        </Route>
      </Route>

      {/* Admin Portal Route Group (Team Members & Admins) */}
      <Route element={<ProtectedRoute allowedRoles={['team_member', 'admin']} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/uploads" replace />} />
          <Route path="uploads" element={<PendingUploads />} />
          <Route path="pending-uploads" element={<PendingUploads />} />
          <Route path="confirm-schema/:batchId" element={<ConfirmSchema />} />
          <Route path="pipeline-health" element={<PipelineHealth />} />
          <Route path="data-quality" element={<DataQualityLog />} />
          <Route path="tenants" element={<Tenants />} />
          <Route path="team" element={<TeamMembers />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};
