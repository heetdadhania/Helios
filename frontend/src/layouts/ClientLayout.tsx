import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
  Home,
  LayoutDashboard,
  DownloadCloud,
  History,
  MessageSquare,
  User,
  Bell,
} from 'lucide-react';
import { Sidebar, NavItem } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';

const clientNavItems: NavItem[] = [
  { label: 'Home', to: '/client/home', icon: Home },
  { label: 'Dashboard', to: '/client/dashboard', icon: LayoutDashboard },
  { label: 'Export', to: '/client/export', icon: DownloadCloud },
  { label: 'Submission History', to: '/client/history', icon: History },
  { label: 'Support', to: '/client/support', icon: MessageSquare },
  { label: 'Profile', to: '/client/profile', icon: User },
  { label: 'Notifications', to: '/client/notifications', icon: Bell },
];

const titleMap: Record<string, string> = {
  '/client/home': 'Home',
  '/client/dashboard': 'Analytics Overview',
  '/client/export': 'Export',
  '/client/history': 'Submission History',
  '/client/submission-history': 'Submission History',
  '/client/support': 'Support & Inquiries',
  '/client/profile': 'User Profile',
  '/client/notifications': 'Notifications & Alerts',
};

export const ClientLayout: React.FC = () => {
  const location = useLocation();
  const currentTitle = titleMap[location.pathname] || 'Organization Portal';

  return (
    <div className="flex min-h-screen bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200">
      <Sidebar portalTitle="Organization Portal" items={clientNavItems} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={currentTitle} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default ClientLayout;
