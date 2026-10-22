import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
  Home,
  Clock,
  Activity,
  CheckCircle2,
  Building2,
  UploadCloud,
  Database,
  History,
  MessageSquare,
  User,
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';
import { useBasePath } from '@/hooks/useBasePath';

const getTeamPageTitle = (pathname: string): string => {
  const normalized = pathname.replace(/^\/(admin|team)/, '');
  if (!normalized || normalized === '/home') return 'Home';
  if (normalized === '/profile') return 'User Profile';
  if (normalized === '/uploads' || normalized === '/pending-uploads') return 'Pending Ingestion Approvals';
  if (normalized === '/upload' || normalized === '/ingest-upload') return 'Ingest File Upload';
  if (normalized === '/connect-db' || normalized === '/connect-database') return 'Connect Database Ingestion';
  if (normalized === '/history' || normalized === '/submission-history') return 'Submission History';
  if (normalized === '/support' || normalized === '/inbox') return 'Support & Update Requests';
  if (normalized === '/pipeline-health') return 'Pipeline Health & Telemetry';
  if (normalized === '/data-quality') return 'Data Quality & Rejection Audit';
  if (normalized === '/tenants') return 'Assigned Organizations';
  return 'Operations Console';
};

export const TeamLayout: React.FC = () => {
  const basePath = useBasePath();
  const location = useLocation();
  const currentTitle = getTeamPageTitle(location.pathname);

  const teamNavItems: NavItem[] = React.useMemo(() => [
    { label: 'Home', to: `${basePath}/home`, icon: Home },
    { label: 'Pending Uploads', to: `${basePath}/uploads`, icon: Clock },
    { label: 'Upload Data', to: `${basePath}/upload`, icon: UploadCloud },
    { label: 'Connect Database', to: `${basePath}/connect-db`, icon: Database },
    { label: 'Submission History', to: `${basePath}/history`, icon: History },
    { label: 'Support Inbox', to: `${basePath}/support`, icon: MessageSquare },
    { label: 'Pipeline Health', to: `${basePath}/pipeline-health`, icon: Activity },
    { label: 'Data Quality', to: `${basePath}/data-quality`, icon: CheckCircle2 },
    { label: 'Organizations', to: `${basePath}/tenants`, icon: Building2 },
    { label: 'Profile', to: `${basePath}/profile`, icon: User },
  ], [basePath]);

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle="Team Portal" items={teamNavItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default TeamLayout;
