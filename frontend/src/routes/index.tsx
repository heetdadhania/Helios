import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ClientLayout } from '@/layouts/ClientLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';

// Pages
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/client/Dashboard';
import { DataSourceSelect } from '@/pages/client/DataSourceSelect';
import { ApiAccess } from '@/pages/client/ApiAccess';
import { ExportDataPage } from '@/pages/client/ExportDataPage';
import { IngestUpload } from '@/pages/team/IngestUpload';
import { IngestDatabaseConnection } from '@/pages/team/IngestDatabaseConnection';
import { PendingUploads } from '@/pages/admin/PendingUploads';
import { ConfirmSchema } from '@/pages/admin/ConfirmSchema';
import { PipelineHealth } from '@/pages/admin/PipelineHealth';
import { DataQualityLog } from '@/pages/admin/DataQualityLog';
import { Tenants } from '@/pages/admin/Tenants';
import { TeamMembers } from '@/pages/admin/TeamMembers';
import { SubmissionHistory } from '@/pages/client/SubmissionHistory';
import { TeamHistory } from '@/pages/team/TeamHistory';
import { AdminHistory } from '@/pages/admin/AdminHistory';
import { SupportInbox } from '@/pages/team/SupportInbox';
import { TenantDashboardView } from '@/pages/admin/TenantDashboardView';
import { TenantHealth } from '@/pages/admin/TenantHealth';
import { TenantComparison } from '@/pages/admin/TenantComparison';
import { UsageDashboard } from '@/pages/admin/UsageDashboard';
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

const HistoryRouteSelector: React.FC = () => {
  const { user } = useAuth();
  return user?.role === 'admin' ? <AdminHistory /> : <TeamHistory />;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Root Redirection */}
      <Route path="/" element={<RootRedirect />} />

      {/* Public Login Route */}
      <Route path="/login" element={<Login />} />

      {/* Client Portal Route Group (SMB Owners & Admins) - Ingestion removed */}
      <Route element={<ProtectedRoute allowedRoles={['smb_owner', 'admin']} />}>
        <Route path="/client" element={<ClientLayout />}>
          <Route index element={<Navigate to="/client/select-source" replace />} />
          <Route path="select-source" element={<DataSourceSelect />} />
          <Route path="data-sources" element={<DataSourceSelect />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="history" element={<SubmissionHistory />} />
          <Route path="submission-history" element={<SubmissionHistory />} />
          <Route path="api-access" element={<ApiAccess />} />
          <Route path="api-keys" element={<ApiAccess />} />
          <Route path="export" element={<ExportDataPage />} />
        </Route>
      </Route>

      {/* Admin & Operations Route Group (Team Members & Admins) */}
      <Route element={<ProtectedRoute allowedRoles={['team_member', 'admin']} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/uploads" replace />} />
          <Route path="uploads" element={<PendingUploads />} />
          <Route path="pending-uploads" element={<PendingUploads />} />
          <Route path="upload" element={<IngestUpload />} />
          <Route path="ingest-upload" element={<IngestUpload />} />
          <Route path="connect-db" element={<IngestDatabaseConnection />} />
          <Route path="connect-database" element={<IngestDatabaseConnection />} />
          <Route path="confirm-schema/:batchId" element={<ConfirmSchema />} />
          <Route path="history" element={<HistoryRouteSelector />} />
          <Route path="submission-history" element={<HistoryRouteSelector />} />
          <Route path="support" element={<SupportInbox />} />
          <Route path="inbox" element={<SupportInbox />} />
          <Route path="pipeline-health" element={<PipelineHealth />} />
          <Route path="data-quality" element={<DataQualityLog />} />
          <Route path="tenants" element={<Tenants />} />
          <Route path="team" element={<TeamMembers />} />
          <Route path="oversight/dashboard/:tenantId" element={<TenantDashboardView />} />
          <Route path="oversight/health" element={<TenantHealth />} />
          <Route path="tenant-health" element={<TenantHealth />} />
          <Route path="oversight/compare" element={<TenantComparison />} />
          <Route path="tenant-compare" element={<TenantComparison />} />
          <Route path="oversight/usage" element={<UsageDashboard />} />
          <Route path="usage" element={<UsageDashboard />} />
        </Route>

        {/* /team routes alias */}
        <Route path="/team" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/upload" replace />} />
          <Route path="upload" element={<IngestUpload />} />
          <Route path="ingest-upload" element={<IngestUpload />} />
          <Route path="connect-db" element={<IngestDatabaseConnection />} />
          <Route path="connect-database" element={<IngestDatabaseConnection />} />
          <Route path="history" element={<TeamHistory />} />
          <Route path="submission-history" element={<TeamHistory />} />
          <Route path="support" element={<SupportInbox />} />
          <Route path="inbox" element={<SupportInbox />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};
