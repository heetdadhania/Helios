import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, DownloadCloud, Database, Key } from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

const clientNavItems: NavItem[] = [
  { label: 'Dashboard', to: '/client/dashboard', icon: LayoutDashboard },
  { label: 'Upload Data', to: '/client/upload', icon: UploadCloud },
  { label: 'Connect Database', to: '/client/connect-db', icon: Database },
  { label: 'API Access', to: '/client/api-access', icon: Key },
  { label: 'Export Datasets', to: '/client/export', icon: DownloadCloud },
];

const titleMap: Record<string, string> = {
  '/client/dashboard': 'Analytics Overview',
  '/client/upload': 'Upload Data Files',
  '/client/connect-db': 'Connect Database Ingestion',
  '/client/connect-database': 'Connect Database Ingestion',
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
