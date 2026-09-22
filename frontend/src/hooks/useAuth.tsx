import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthContextType, LoginCredentials, User, UserRole } from '@/types/auth';
import { authService } from '@/services/authService';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = () => {
      const savedToken = localStorage.getItem('helios_token');
      const savedUserStr = localStorage.getItem('helios_user');
      if (savedToken && savedUserStr) {
        try {
          const parsedUser = JSON.parse(savedUserStr);
          setUser(parsedUser);
          setToken(savedToken);
        } catch {
          authService.logout();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const response = await authService.login(credentials);
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem('helios_token', response.access_token);
      localStorage.setItem('helios_user', JSON.stringify(response.user));
      if (response.user.tenant_id) {
        localStorage.setItem('helios_tenant_id', String(response.user.tenant_id));
      } else {
        localStorage.removeItem('helios_tenant_id');
      }
      return response.user;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setToken(null);
  };

  const role: UserRole | null = user?.role || null;
  const isAuthenticated = !!token && !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        isAuthenticated,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
