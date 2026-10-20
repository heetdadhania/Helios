import React from 'react';
import { Outlet } from 'react-router-dom';
import { HeliosLogo } from '@/components/HeliosLogo';
import { ThemeToggle } from '@/components/ThemeToggle';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-helios-bg-light dark:bg-helios-bg-dark transition-colors duration-200 relative">
      {/* Absolute theme toggle on top right */}
      <div className="absolute top-5 right-5">
        <ThemeToggle />
      </div>

      {/* Main Split-Screen Card */}
      <div className="w-full max-w-4xl min-h-[580px] rounded-card overflow-hidden shadow-soft border border-helios-border-light dark:border-helios-border-dark flex flex-col md:flex-row bg-helios-card-light dark:bg-helios-card-dark transition-colors">
        
        {/* Left Branding Panel (~50% width, gradient background with blue accent, rounded outer edge) */}
        <div className="relative md:w-1/2 p-8 lg:p-10 flex flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-900 text-white rounded-t-card md:rounded-tr-none md:rounded-l-card">
          {/* Top-left Helios logo in branding panel */}
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/15">
              <HeliosLogo size={24} showWordmark={true} className="text-white brightness-125" />
            </div>

            <div className="mt-8">
              <span className="text-xs font-semibold tracking-wider uppercase text-blue-200">
                Enterprise Multi-Organization Engine
              </span>
              <h2 className="mt-2 text-2xl lg:text-3xl font-extrabold tracking-tight leading-tight">
                Designed for high-growth e-commerce teams.
              </h2>
              <p className="mt-3 text-sm text-blue-100/80 leading-relaxed">
                Connect your operational stores, automate Delta Lake pipelines, and synchronize enterprise telemetry in real time.
              </p>
            </div>
          </div>

          {/* Stylized / blurred preview of the dashboard peeking up from the bottom */}
          <div className="relative z-0 mt-6 -mb-12 -mr-10 opacity-90 transition-transform duration-500 hover:scale-[1.02]">
            <div className="w-[120%] p-4 rounded-card bg-helios-card-dark/80 backdrop-blur-md border border-white/20 shadow-2xl space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  <span className="text-[10px] font-mono text-blue-200 ml-2">sales_sync_daily.delta</span>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">
                  LIVE 99.98%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-white/5 border border-white/10">
                  <div className="text-[10px] text-blue-200">Monthly GMV</div>
                  <div className="text-sm font-bold text-white mt-0.5">₹8,42,910</div>
                </div>
                <div className="p-2.5 rounded bg-white/5 border border-white/10">
                  <div className="text-[10px] text-blue-200">Sync Latency</div>
                  <div className="text-sm font-bold text-emerald-300 mt-0.5">142ms</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Form Panel (~50% width, matches current theme) */}
        <div className="md:w-1/2 p-8 lg:p-10 flex flex-col justify-center bg-helios-card-light dark:bg-helios-card-dark transition-colors">
          <Outlet />
        </div>

      </div>
    </div>
  );
};
