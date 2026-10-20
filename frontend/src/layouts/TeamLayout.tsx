import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
  Clock,
  Activity,
  CheckCircle2,
  Building2,
  UploadCloud,
  Database,
  History,
  MessageSquare,
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

const teamNavItems: NavItem[] = [
  { label: 'Pending Uploads', to: '/admin/uploads', icon: Clock },
  { label: 'Upload Data', to: '/admin/upload', icon: UploadCloud },
  { label: 'Connect Database', to: '/admin/connect-db', icon: Database },
  { label: 'Submission History', to: '/admin/history', icon: History },
  { label: 'Support Inbox', to: '/admin/support', icon: MessageSquare },
  { label: 'Pipeline Health', to: '/admin/pipeline-health', icon: Activity },
  { label: 'Data Quality', to: '/admin/data-quality', icon: CheckCircle2 },
  { label: 'Organizations', to: '/admin/tenants', icon: Building2 },
];

const teamTitleMap: Record<string, string> = {
  '/admin/uploads': 'Pending Ingestion Approvals',
  '/admin/pending-uploads': 'Pending Ingestion Approvals',
  '/admin/upload': 'Ingest File Upload',
  '/admin/ingest-upload': 'Ingest File Upload',
  '/admin/connect-db': 'Connect Database Ingestion',
  '/admin/connect-database': 'Connect Database Ingestion',
  '/admin/history': 'Submission History',
  '/team/history': 'Submission History',
  '/admin/support': 'Support & Update Requests',
  '/team/support': 'Support & Update Requests',
  '/team/upload': 'Ingest File Upload',
  '/team/ingest-upload': 'Ingest File Upload',
  '/team/connect-db': 'Connect Database Ingestion',
  '/team/connect-database': 'Connect Database Ingestion',
  '/admin/pipeline-health': 'Pipeline Health & Telemetry',
  '/admin/data-quality': 'Data Quality & Rejection Audit',
  '/admin/tenants': 'Assigned Organizations',
};

export const TeamLayout: React.FC = () => {
  const location = useLocation();
  const currentPath = location.pathname;
  const currentTitle = teamTitleMap[currentPath] || 'Operations Console';

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
