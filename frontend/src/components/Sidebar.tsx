import React from 'react';
import { NavLink } from 'react-router-dom';
import { LucideIcon } from 'lucide-react';
import { HeliosLogo } from './HeliosLogo';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  badge?: string;
}

interface SidebarProps {
  portalTitle: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ portalTitle, items }) => {
  return (
    <aside className="w-64 shrink-0 flex flex-col justify-between border-r border-helios-border-light dark:border-helios-border-dark bg-helios-sidebar-light dark:bg-helios-sidebar-dark transition-colors duration-200 min-h-screen">
      <div>
        {/* Top Logo & Portal Badge */}
        <div className="h-16 px-6 flex items-center justify-between border-b border-helios-border-light dark:border-helios-border-dark">
          <HeliosLogo size={28} />
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-helios-accent-blue/10 text-helios-accent-blue border border-helios-accent-blue/20">
            {portalTitle}
          </span>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-control text-xs font-medium transition-all duration-150 group ${
                    isActive
                      ? 'border-l-4 border-helios-accent-teal bg-helios-accent-teal/10 text-helios-accent-teal font-semibold'
                      : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 transition-colors group-hover:scale-105" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-500 font-semibold">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Tenant Environment Tag */}
      <div className="p-4 m-3 rounded-card bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-xs">
        <div className="flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          <span className="w-2 h-2 rounded-full bg-helios-accent-teal animate-pulse" />
          <span className="text-[11px] font-mono truncate">Unity Catalog: Connected</span>
        </div>
        <div className="mt-1 text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark truncate">
          Delta Lake Engine v3.1
        </div>
      </div>
    </aside>
  );
};
