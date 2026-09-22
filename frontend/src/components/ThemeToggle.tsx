import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`p-2 rounded-control text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-helios-accent-blue ${className}`}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? (
        <Sun className="w-5 h-5 text-amber-400 transition-transform hover:rotate-45 duration-200" />
      ) : (
        <Moon className="w-5 h-5 text-indigo-600 transition-transform hover:-rotate-12 duration-200" />
      )}
    </button>
  );
};
