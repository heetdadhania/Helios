import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ClientLayout } from '@/layouts/ClientLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';
import { Loader2 } from 'lucide-react';

// Lazy-loaded route components for efficient bundle code-splitting
const Login = lazy(() => import('@/pages/Login').then((m) => ({ default: m.Login })));
const Dashboard = lazy(() => import('@/pages/client/Dashboard').then((m) => ({ default: m.Dashboard })));
const DataSourceSelect = lazy(() => import('@/pages/client/DataSourceSelect').then((m) => ({ default: m.DataSourceSelect })));
const ApiAccess = lazy(() => import('@/pages/client/ApiAccess').then((m) => ({ default: m.ApiAccess })));
const ExportDataPage = lazy(() => import('@/pages/client/ExportDataPage').then((m) => ({ default: m.ExportDataPage })));
const IngestUpload = lazy(() => import('@/pages/team/IngestUpload').then((m) => ({ default: m.IngestUpload })));
const IngestDatabaseConnection = lazy(() => import('@/pages/team/IngestDatabaseConnection').then((m) => ({ default: m.IngestDatabaseConnection })));
const PendingUploads = lazy(() => import('@/pages/admin/PendingUploads').then((m) => ({ default: m.PendingUploads })));
const ConfirmSchema = lazy(() => import('@/pages/admin/ConfirmSchema').then((m) => ({ default: m.ConfirmSchema })));
const PipelineHealth = lazy(() => import('@/pages/admin/PipelineHealth').then((m) => ({ default: m.PipelineHealth })));
const DataQualityLog = lazy(() => import('@/pages/admin/DataQualityLog').then((m) => ({ default: m.DataQualityLog })));
const Tenants = lazy(() => import('@/pages/admin/Tenants').then((m) => ({ default: m.Tenants })));
const TeamMembers = lazy(() => import('@/pages/admin/TeamMembers').then((m) => ({ default: m.TeamMembers })));
const SubmissionHistory = lazy(() => import('@/pages/client/SubmissionHistory').then((m) => ({ default: m.SubmissionHistory })));
const TeamHistory = lazy(() => import('@/pages/team/TeamHistory').then((m) => ({ default: m.TeamHistory })));
const AdminHistory = lazy(() => import('@/pages/admin/AdminHistory').then((m) => ({ default: m.AdminHistory })));
const SupportInbox = lazy(() => import('@/pages/team/SupportInbox').then((m) => ({ default: m.SupportInbox })));
const TenantDashboardView = lazy(() => import('@/pages/admin/TenantDashboardView').then((m) => ({ default: m.TenantDashboardView })));
const TenantHealth = lazy(() => import('@/pages/admin/TenantHealth').then((m) => ({ default: m.TenantHealth })));
const TenantComparison = lazy(() => import('@/pages/admin/TenantComparison').then((m) => ({ default: m.TenantComparison })));
const UsageDashboard = lazy(() => import('@/pages/admin/UsageDashboard').then((m) => ({ default: m.UsageDashboard })));
const ChangePassword = lazy(() => import('@/pages/auth/ChangePassword').then((m) => ({ default: m.ChangePassword })));

const RouteLoadingFallback: React.FC = () => (
  <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
    <Loader2 className="w-8 h-8 animate-spin text-helios-accent-blue mb-3" />
    <span className="text-xs font-medium">Loading view...</span>
  </div>
);

const RootRedirect: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  return user.role === 'smb_owner' ? (
    <Navigate to="/client/select-source" replace />
  ) : (
    <Navigate to="/admin/uploads" replace />
  );
};

const ChangePasswordGuard: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  if (!user.must_change_password) {
    return user.role === 'smb_owner' ? (
      <Navigate to="/client/dashboard" replace />
    ) : (
      <Navigate to="/admin/uploads" replace />
    );
  }
  return <ChangePassword />;
};

const HistoryRouteSelector: React.FC = () => {
  const { user } = useAuth();
  return user?.role === 'admin' ? <AdminHistory /> : <TeamHistory />;
};

export const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Routes>
      {/* Root Redirection */}
      <Route path="/" element={<RootRedirect />} />

      {/* Public Login Route */}
      <Route path="/login" element={<Login />} />

      {/* Mandatory First-Login Password Change Route */}
      <Route path="/change-password" element={<ChangePasswordGuard />} />

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
  </Suspense>
  );
};
