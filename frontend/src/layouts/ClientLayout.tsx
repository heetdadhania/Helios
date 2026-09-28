import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, DownloadCloud, Key, Layers, History } from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

const clientNavItems: NavItem[] = [
  { label: 'Data Sources', to: '/client/select-source', icon: Layers },
  { label: 'Dashboard', to: '/client/dashboard', icon: LayoutDashboard },
  { label: 'Submission History', to: '/client/history', icon: History },
  { label: 'API Access', to: '/client/api-access', icon: Key },
  { label: 'Export Datasets', to: '/client/export', icon: DownloadCloud },
];

const titleMap: Record<string, string> = {
  '/client/select-source': 'Data Ingestion Sources',
  '/client/data-sources': 'Data Ingestion Sources',
  '/client/dashboard': 'Analytics Overview',
  '/client/history': 'Submission History',
  '/client/submission-history': 'Submission History',
  '/client/api-access': 'Programmatic API Access',
  '/client/api-keys': 'Programmatic API Access',
  '/client/export': 'Export Datasets',
};

export const ClientLayout: React.FC = () => {
  const location = useLocation();
  const currentTitle = titleMap[location.pathname] || 'Client Portal';

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle="Client Portal" items={clientNavItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
