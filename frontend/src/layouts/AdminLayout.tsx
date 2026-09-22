import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
  Clock,
  Activity,
  CheckCircle2,
  Building2,
  Users,
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

const adminNavItems: NavItem[] = [
  { label: 'Pending Uploads', to: '/admin/uploads', icon: Clock, badge: '3' },
  { label: 'Pipeline Health', to: '/admin/pipeline-health', icon: Activity },
  { label: 'Data Quality', to: '/admin/data-quality', icon: CheckCircle2 },
  { label: 'Tenants', to: '/admin/tenants', icon: Building2 },
  { label: 'Team', to: '/admin/team', icon: Users },
];

const adminTitleMap: Record<string, string> = {
  '/admin/uploads': 'Pending Data Approvals',
  '/admin/pending-uploads': 'Pending Data Approvals',
  '/admin/pipeline-health': 'Pipeline Health & Telemetry',
  '/admin/data-quality': 'Data Quality & Schemas',
  '/admin/tenants': 'Tenant Management',
  '/admin/team': 'Team & Role Assignments',
};

export const AdminLayout: React.FC = () => {
  const location = useLocation();
  const currentTitle = adminTitleMap[location.pathname] || 'Admin Console';

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle="Admin Portal" items={adminNavItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
