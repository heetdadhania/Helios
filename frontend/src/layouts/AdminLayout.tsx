import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
  Home,
  Clock,
  Activity,
  CheckCircle2,
  Building2,
  Users,
  UploadCloud,
  Database,
  History,
  MessageSquare,
  BarChart3,
  TrendingUp,
  ShieldAlert,
  User,
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';
import { useAuth } from '@/hooks/useAuth';
import { useBasePath } from '@/hooks/useBasePath';

const getPageTitle = (pathname: string): string => {
  const normalized = pathname.replace(/^\/(admin|team)/, '');
  if (!normalized || normalized === '/home') return 'Home';
  if (normalized === '/profile') return 'User Profile';
  if (normalized === '/uploads' || normalized === '/pending-uploads') return 'Pending Ingestion Approvals';
  if (normalized === '/upload' || normalized === '/ingest-upload') return 'Ingest File Upload';
  if (normalized === '/connect-db' || normalized === '/connect-database') return 'Connect Database Ingestion';
  if (normalized === '/history' || normalized === '/submission-history') return 'Submission History';
  if (normalized === '/support' || normalized === '/inbox') return 'Support & Update Requests';
  if (normalized.startsWith('/confirm-schema')) return 'Confirm Ingestion Schema';
  if (normalized === '/pipeline-health') return 'Pipeline Health & Telemetry';
  if (normalized === '/data-quality') return 'Data Quality & Rejection Audit';
  if (normalized === '/tenants') return 'Organization Management';
  if (normalized === '/team') return 'Team & Role Assignments';
  if (normalized.startsWith('/oversight/dashboard')) return 'Organization Dashboard (Admin View-As)';
  if (normalized === '/oversight/health' || normalized === '/tenant-health') return 'Organization Health & SLA Oversight';
  if (normalized === '/oversight/compare' || normalized === '/tenant-compare') return 'Cross-Organization Comparison';
  if (normalized === '/oversight/usage' || normalized === '/usage') return 'Platform Usage & Telemetry';
  return 'Operations Console';
};

export const AdminLayout: React.FC = () => {
  const { user } = useAuth();
  const basePath = useBasePath();
  const location = useLocation();

  const currentTitle = getPageTitle(location.pathname);

  const navItems = React.useMemo<NavItem[]>(() => {
    const items: NavItem[] = [
      { label: 'Home', to: `${basePath}/home`, icon: Home },
      { label: 'Pending Uploads', to: `${basePath}/uploads`, icon: Clock },
      { label: 'Upload Data', to: `${basePath}/upload`, icon: UploadCloud },
      { label: 'Connect Database', to: `${basePath}/connect-db`, icon: Database },
      { label: 'Submission History', to: `${basePath}/history`, icon: History },
      { label: 'Support Inbox', to: `${basePath}/support`, icon: MessageSquare },
      { label: 'Pipeline Health', to: `${basePath}/pipeline-health`, icon: Activity },
      { label: 'Data Quality', to: `${basePath}/data-quality`, icon: CheckCircle2 },
      { label: 'Organizations', to: `${basePath}/tenants`, icon: Building2 },
    ];

    if (user?.role === 'admin') {
      items.push(
        { label: 'Organization Health', to: '/admin/oversight/health', icon: ShieldAlert },
        { label: 'Compare Organizations', to: '/admin/oversight/compare', icon: BarChart3 },
        { label: 'Platform Usage', to: '/admin/oversight/usage', icon: TrendingUp },
        { label: 'Team', to: '/admin/team', icon: Users }
      );
    }

    items.push({ label: 'Profile', to: `${basePath}/profile`, icon: User });
    return items;
  }, [basePath, user?.role]);

  const portalTitle = user?.role === 'admin' ? 'Admin Portal' : 'Operations Portal';

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle={portalTitle} items={navItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
