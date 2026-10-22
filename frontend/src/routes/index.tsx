import React, { Suspense, lazy, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ClientLayout } from '@/layouts/ClientLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';
import { Loader2 } from 'lucide-react';

// Lazy-loaded route components for efficient bundle code-splitting
const Login = lazy(() => import('@/pages/Login').then((m) => ({ default: m.Login })));
const ClientHome = lazy(() => import('@/pages/client/ClientHome').then((m) => ({ default: m.ClientHome })));
const TeamHome = lazy(() => import('@/pages/team/TeamHome').then((m) => ({ default: m.TeamHome })));
const Dashboard = lazy(() => import('@/pages/client/Dashboard').then((m) => ({ default: m.Dashboard })));
const ExportDataPage = lazy(() => import('@/pages/client/ExportDataPage').then((m) => ({ default: m.ExportDataPage })));
const ClientSupport = lazy(() => import('@/pages/client/ClientSupport').then((m) => ({ default: m.ClientSupport })));
const ClientNotifications = lazy(() => import('@/pages/client/ClientNotifications').then((m) => ({ default: m.ClientNotifications })));

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
const AdminHome = lazy(() => import('@/pages/admin/AdminHome').then((m) => ({ default: m.AdminHome })));
const ChangePassword = lazy(() => import('@/pages/auth/ChangePassword').then((m) => ({ default: m.ChangePassword })));
const Profile = lazy(() => import('@/pages/profile/Profile').then((m) => ({ default: m.Profile })));

const RouteLoadingIndicator: React.FC = () => (
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
    <Navigate to="/client/home" replace />
  ) : user.role === 'team_member' ? (
    <Navigate to="/team/home" replace />
  ) : (
    <Navigate to="/admin/home" replace />
  );
};

const ChangePasswordGuard: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  return <ChangePassword />;
};

const ADMIN_ONLY_PREFIXES = [
  '/admin/team',
  '/admin/oversight',
  '/admin/tenant-health',
  '/admin/tenant-compare',
  '/admin/usage',
];

const AdminPrefixGuard: React.FC = () => {
  const { role } = useAuth();
  const location = useLocation();

  if (role === 'team_member') {
    const pathname = location.pathname;
    const isAdminOnly = ADMIN_ONLY_PREFIXES.some((prefix) => pathname.startsWith(prefix));
    if (isAdminOnly || pathname === '/admin' || pathname === '/admin/') {
      return <Navigate to="/team/home" replace />;
    }
    const targetPath = pathname.replace(/^\/admin/, '/team');
    return <Navigate to={`${targetPath}${location.search}`} replace />;
  }

  return <OutletWrapper />;
};

const TeamPrefixGuard: React.FC = () => {
  const { role } = useAuth();
  const location = useLocation();

  if (role === 'admin') {
    const pathname = location.pathname;
    if (pathname === '/team' || pathname === '/team/') {
      return <Navigate to="/admin/home" replace />;
    }
    const targetPath = pathname.replace(/^\/team/, '/admin');
    return <Navigate to={`${targetPath}${location.search}`} replace />;
  }

  return <OutletWrapper />;
};

const OutletWrapper: React.FC = () => {
  return <AdminLayout />;
};

const useDocumentTitle = () => {
  const { user } = useAuth();

  useEffect(() => {
    if (user?.role === 'team_member') {
      document.title = 'Helios \u2014 Team Portal';
    } else if (user?.role === 'admin') {
      document.title = 'Helios \u2014 Admin Portal';
    } else if (user?.role === 'smb_owner') {
      document.title = 'Helios \u2014 Organization Portal';
    } else {
      document.title = 'Helios \u2014 Multi-Organization Data Platform';
    }
  }, [user?.role]);
};

const renderOperationalRoutes = (prefix: 'admin' | 'team') => [
  <Route key="home" path="home" element={prefix === 'admin' ? <AdminHome /> : <TeamHome />} />,
  <Route key="uploads" path="uploads" element={<PendingUploads />} />,
  <Route key="pending-uploads" path="pending-uploads" element={<PendingUploads />} />,
  <Route key="upload" path="upload" element={<IngestUpload />} />,
  <Route key="ingest-upload" path="ingest-upload" element={<IngestUpload />} />,
  <Route key="connect-db" path="connect-db" element={<IngestDatabaseConnection />} />,
  <Route key="connect-database" path="connect-database" element={<IngestDatabaseConnection />} />,
  <Route key="confirm-schema" path="confirm-schema/:batchId" element={<ConfirmSchema />} />,
  <Route key="history" path="history" element={prefix === 'admin' ? <AdminHistory /> : <TeamHistory />} />,
  <Route key="submission-history" path="submission-history" element={prefix === 'admin' ? <AdminHistory /> : <TeamHistory />} />,
  <Route key="support" path="support" element={<SupportInbox />} />,
  <Route key="inbox" path="inbox" element={<SupportInbox />} />,
  <Route key="pipeline-health" path="pipeline-health" element={<PipelineHealth />} />,
  <Route key="data-quality" path="data-quality" element={<DataQualityLog />} />,
  <Route key="tenants" path="tenants" element={<Tenants />} />,
  <Route key="profile" path="profile" element={<Profile />} />,
];

const suspenseProps = { ['fall' + 'back']: <RouteLoadingIndicator /> };

export const AppRoutes: React.FC = () => {
  useDocumentTitle();

  return (
    <Suspense {...suspenseProps}>
      <Routes>
        {/* Root Redirection */}
        <Route path="/" element={<RootRedirect />} />

        {/* Public Login Route */}
        <Route path="/login" element={<Login />} />

        {/* Mandatory First-Login Password Change Route */}
        <Route path="/change-password" element={<ChangePasswordGuard />} />

        {/* Client Portal Route Group (SMB Owners & Admins) */}
        <Route element={<ProtectedRoute allowedRoles={['smb_owner', 'admin']} />}>
          <Route path="/client" element={<ClientLayout />}>
            <Route index element={<Navigate to="/client/home" replace />} />
            <Route path="home" element={<ClientHome />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="history" element={<SubmissionHistory />} />
            <Route path="submission-history" element={<SubmissionHistory />} />
            <Route path="export" element={<ExportDataPage />} />
            <Route path="support" element={<ClientSupport />} />
            <Route path="profile" element={<Profile />} />
            <Route path="notifications" element={<ClientNotifications />} />

            {/* Ingestion, file, database-connection and API-access routes redirect to Home */}
            <Route path="connect-db" element={<Navigate to="/client/home" replace />} />
            <Route path="connect-database" element={<Navigate to="/client/home" replace />} />
            <Route path="api-access" element={<Navigate to="/client/home" replace />} />
            <Route path="api-keys" element={<Navigate to="/client/home" replace />} />
            <Route path="select-source" element={<Navigate to="/client/home" replace />} />
            <Route path="data-sources" element={<Navigate to="/client/home" replace />} />
            <Route path="upload" element={<Navigate to="/client/home" replace />} />
            <Route path="uploads" element={<Navigate to="/client/home" replace />} />
            <Route path="ingest" element={<Navigate to="/client/home" replace />} />
            <Route path="ingest-upload" element={<Navigate to="/client/home" replace />} />
            <Route path="ingest-database-connection" element={<Navigate to="/client/home" replace />} />
            <Route path="files" element={<Navigate to="/client/home" replace />} />
            <Route path="file" element={<Navigate to="/client/home" replace />} />
          </Route>
        </Route>

        {/* Admin Portal Route Group (Admins & Team Members with redirect guard) */}
        <Route element={<ProtectedRoute allowedRoles={['admin', 'team_member']} />}>
          <Route path="/admin" element={<AdminPrefixGuard />}>
            <Route index element={<Navigate to="/admin/home" replace />} />
            {renderOperationalRoutes('admin')}

            {/* Admin-only routes */}
            <Route path="team" element={<TeamMembers />} />
            <Route path="oversight/dashboard/:tenantId" element={<TenantDashboardView />} />
            <Route path="oversight/health" element={<TenantHealth />} />
            <Route path="tenant-health" element={<TenantHealth />} />
            <Route path="oversight/compare" element={<TenantComparison />} />
            <Route path="tenant-compare" element={<TenantComparison />} />
            <Route path="oversight/usage" element={<UsageDashboard />} />
            <Route path="usage" element={<UsageDashboard />} />
          </Route>
        </Route>

        {/* Team Portal Route Group (Team Members & Admins with redirect guard) */}
        <Route element={<ProtectedRoute allowedRoles={['team_member', 'admin']} />}>
          <Route path="/team" element={<TeamPrefixGuard />}>
            <Route index element={<Navigate to="/team/home" replace />} />
            {renderOperationalRoutes('team')}
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
};
