import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';

export interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const THEME_STORAGE_KEY = 'helios_theme';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

/**
 * Apply theme classes and attributes to document root element
 * so all Tailwind `dark:` variants and data-theme CSS variables key off of it.
 */
export function applyThemeToDocument(theme: Theme): void {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add('dark');
    root.setAttribute('data-theme', 'dark');
  } else {
    root.classList.remove('dark');
    root.setAttribute('data-theme', 'light');
  }
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}

/**
 * Resolve initial theme from localStorage or default to 'dark'.
 */
export function getInitialTheme(): Theme {
  const saved = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
  if (saved === 'dark' || saved === 'light') {
    return saved;
  }
  return 'dark';
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyThemeToDocument(theme);
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return React.createElement(
    ThemeContext.Provider,
    { value: { theme, toggleTheme, setTheme } },
    children
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default useTheme;
