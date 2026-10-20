import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
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
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

import { useAuth } from '@/hooks/useAuth';

const adminNavItems: NavItem[] = [
  { label: 'Pending Uploads', to: '/admin/uploads', icon: Clock },
  { label: 'Upload Data', to: '/admin/upload', icon: UploadCloud },
  { label: 'Connect Database', to: '/admin/connect-db', icon: Database },
  { label: 'Submission History', to: '/admin/history', icon: History },
  { label: 'Support Inbox', to: '/admin/support', icon: MessageSquare },
  { label: 'Pipeline Health', to: '/admin/pipeline-health', icon: Activity },
  { label: 'Data Quality', to: '/admin/data-quality', icon: CheckCircle2 },
  { label: 'Organizations', to: '/admin/tenants', icon: Building2 },
  { label: 'Organization Health', to: '/admin/oversight/health', icon: ShieldAlert },
  { label: 'Compare Organizations', to: '/admin/oversight/compare', icon: BarChart3 },
  { label: 'Platform Usage', to: '/admin/oversight/usage', icon: TrendingUp },
  { label: 'Team', to: '/admin/team', icon: Users },
];

const adminTitleMap: Record<string, string> = {
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
  '/admin/confirm-schema': 'Confirm Ingestion Schema',
  '/admin/pipeline-health': 'Pipeline Health & Telemetry',
  '/admin/data-quality': 'Data Quality & Rejection Audit',
  '/admin/tenants': 'Organization Management',
  '/admin/team': 'Team & Role Assignments',
  '/admin/oversight/health': 'Organization Health & SLA Oversight',
  '/admin/tenant-health': 'Organization Health & SLA Oversight',
  '/admin/oversight/compare': 'Cross-Organization Comparison',
  '/admin/tenant-compare': 'Cross-Organization Comparison',
  '/admin/oversight/usage': 'Platform Usage & Telemetry',
  '/admin/usage': 'Platform Usage & Telemetry',
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
    } else if (currentPath.startsWith('/admin/oversight/dashboard')) {
      currentTitle = 'Organization Dashboard (Admin View-As)';
    } else {
      currentTitle = user?.role === 'admin' ? 'Admin Console' : 'Operations Console';
    }
  }

  // Team Member sees only assigned tenants and operational screens; Admin sees everything plus Oversight & Team
  const navItems = React.useMemo(() => {
    if (user?.role === 'admin') {
      return adminNavItems;
    }
    const adminOnlyRoutes = [
      '/admin/team',
      '/admin/oversight/health',
      '/admin/oversight/compare',
      '/admin/oversight/usage',
    ];
    return adminNavItems.filter((item) => !adminOnlyRoutes.includes(item.to));
  }, [user?.role]);

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
