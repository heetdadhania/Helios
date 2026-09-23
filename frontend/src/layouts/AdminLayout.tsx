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

import { useAuth } from '@/hooks/useAuth';

const adminNavItems: NavItem[] = [
  { label: 'Pending Uploads', to: '/admin/uploads', icon: Clock },
  { label: 'Pipeline Health', to: '/admin/pipeline-health', icon: Activity },
  { label: 'Data Quality', to: '/admin/data-quality', icon: CheckCircle2 },
  { label: 'Tenants', to: '/admin/tenants', icon: Building2 },
  { label: 'Team', to: '/admin/team', icon: Users },
];

const adminTitleMap: Record<string, string> = {
  '/admin/uploads': 'Pending Ingestion Approvals',
  '/admin/pending-uploads': 'Pending Ingestion Approvals',
  '/admin/confirm-schema': 'Confirm Ingestion Schema',
  '/admin/pipeline-health': 'Pipeline Health & Telemetry',
  '/admin/data-quality': 'Data Quality & Rejection Audit',
  '/admin/tenants': 'Tenant Management',
  '/admin/team': 'Team & Role Assignments',
};

export const AdminLayout: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();

  // Determine current title or prefix match for dynamic routes (e.g. /admin/confirm-schema/:id)
  const currentPath = location.pathname;
  let currentTitle = adminTitleMap[currentPath];
  if (!currentTitle) {
    if (currentPath.startsWith('/admin/confirm-schema')) {
      currentTitle = 'Confirm Ingestion Schema';
    } else {
      currentTitle = 'Admin Console';
    }
  }

  // Team Member sees only assigned tenants and operational screens; Admin sees everything plus Team
  const navItems = React.useMemo(() => {
    if (user?.role === 'admin') {
      return adminNavItems;
    }
    return adminNavItems.filter((item) => item.to !== '/admin/team');
  }, [user?.role]);

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle="Admin Portal" items={navItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
