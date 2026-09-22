import React from 'react';

interface HeliosLogoProps {
  size?: number;
  showWordmark?: boolean;
  className?: string;
  themeInvert?: boolean;
}

export const HeliosLogo: React.FC<HeliosLogoProps> = ({
  size = 32,
  showWordmark = true,
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-300 hover:rotate-45"
      >
        <defs>
          <linearGradient id="heliosGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#10B981" />
          </linearGradient>
        </defs>
        {/* Glowing central sphere */}
        <circle cx="16" cy="16" r="5" fill="url(#heliosGrad)" />
        {/* Cardinal rays */}
        <line x1="16" y1="2.5" x2="16" y2="7" stroke="url(#heliosGrad)" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="16" y1="25" x2="16" y2="29.5" stroke="url(#heliosGrad)" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="2.5" y1="16" x2="7" y2="16" stroke="url(#heliosGrad)" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="25" y1="16" x2="29.5" y2="16" stroke="url(#heliosGrad)" strokeWidth="2.5" strokeLinecap="round" />
        {/* Diagonal rays */}
        <line x1="6.5" y1="6.5" x2="9.8" y2="9.8" stroke="url(#heliosGrad)" strokeWidth="2" strokeLinecap="round" />
        <line x1="22.2" y1="22.2" x2="25.5" y2="25.5" stroke="url(#heliosGrad)" strokeWidth="2" strokeLinecap="round" />
        <line x1="6.5" y1="25.5" x2="9.8" y2="22.2" stroke="url(#heliosGrad)" strokeWidth="2" strokeLinecap="round" />
        <line x1="22.2" y1="9.8" x2="25.5" y2="6.5" stroke="url(#heliosGrad)" strokeWidth="2" strokeLinecap="round" />
      </svg>
      {showWordmark && (
        <span className="text-xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
          Helios
        </span>
      )}
    </div>
  );
};
