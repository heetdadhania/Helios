/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        gray: {
          750: '#2d3748',
          850: '#1a202c',
        },
        helios: {
          bg: {
            dark: '#0A0A0A',
            light: '#FAFAFA',
          },
          sidebar: {
            dark: '#111111',
            light: '#FFFFFF',
          },
          card: {
            dark: '#161616',
            light: '#FFFFFF',
          },
          border: {
            dark: '#262626',
            light: '#E5E7EB',
          },
          text: {
            primary: {
              dark: '#F5F5F5',
              light: '#111827',
            },
            secondary: {
              dark: '#A3A3A3',
              light: '#6B7280',
            },
          },
          accent: {
            teal: '#10B981',
            blue: '#3B82F6',
          },
          warning: '#F59E0B',
          error: '#EF4444',
        },
      },
      borderRadius: {
        card: '12px',
        control: '8px',
      },
      boxShadow: {
        soft: '0 4px 20px -2px rgba(0, 0, 0, 0.25)',
      },
    },
  },
  plugins: [],
};
