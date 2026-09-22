import React from 'react';
import { Bell, Search } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { useAuth } from '@/hooks/useAuth';

interface TopBarProps {
  title: string;
}

export const TopBar: React.FC<TopBarProps> = ({ title }) => {
  const { user, logout } = useAuth();
  const initials = user?.name
    ? user.name.substring(0, 2).toUpperCase()
    : 'HE';

  return (
    <header className="h-16 px-6 flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark bg-helios-sidebar-light dark:bg-helios-sidebar-dark transition-colors duration-200">
      {/* Page Title */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
          {title}
        </h1>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
          <input
            type="text"
            placeholder="Search datasets, tables..."
            className="w-56 lg:w-72 pl-9 pr-3 py-1.5 text-xs rounded-control bg-helios-bg-light dark:bg-helios-bg-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark placeholder-helios-text-secondary-light dark:placeholder-helios-text-secondary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
          />
        </div>

        {/* Notification Bell with unread dot */}
        <button
          type="button"
          className="relative p-2 rounded-control text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-helios-accent-blue ring-2 ring-helios-sidebar-light dark:ring-helios-sidebar-dark" />
        </button>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* User Initials Avatar */}
        <div className="relative group pl-2">
          <button
            type="button"
            className="w-8 h-8 rounded-full bg-gradient-to-tr from-helios-accent-blue to-helios-accent-teal text-white flex items-center justify-center text-xs font-bold shadow-sm focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
            title={`${user?.email || 'User'} (${user?.role})`}
          >
            {initials}
          </button>
          {/* Quick logout popover */}
          <div className="absolute right-0 mt-2 w-48 py-1 rounded-control bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-soft hidden group-hover:block z-50">
            <div className="px-3 py-2 border-b border-helios-border-light dark:border-helios-border-dark">
              <p className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark truncate">
                {user?.email}
              </p>
              <p className="text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase mt-0.5">
                Role: {user?.role}
              </p>
            </div>
            <button
              onClick={logout}
              className="w-full text-left px-3 py-2 text-xs text-helios-error hover:bg-black/5 dark:hover:bg-white/5"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
