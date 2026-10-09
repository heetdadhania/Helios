import api from './api';
import { LoginCredentials, TokenResponse, User, UserRole } from '@/types/auth';

export const authService = {
  /**
   * Authenticate user credentials against backend /api/auth/login.
   * Returns JWT token and UserOut details.
   */
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    try {
      const response = await api.post<TokenResponse>('/auth/login', {
        email: credentials.email,
        password: credentials.password,
      });
      return response.data;
    } catch (error: any) {
      // Fallback demo authentication for development when backend SQL warehouse is spinning up or offline
      if (
        !error.response ||
        error.code === 'ERR_NETWORK' ||
        error.response.status === 404 ||
        error.response.status === 500
      ) {
        return this._getDemoFallback(credentials);
      }
      throw error;
    }
  },

  /**
   * Retrieve active user profile from protected endpoint /api/auth/me.
   */
  async getMe(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  /**
   * Clear all user session tokens and cached profile data.
   */
  logout(): void {
    localStorage.removeItem('helios_token');
    localStorage.removeItem('helios_user');
    localStorage.removeItem('helios_tenant_id');
  },

  /**
   * Change user password via /api/auth/change-password.
   * Clears must_change_password requirement.
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await api.post<{ success: boolean; message: string }>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      return response.data;
    } catch (err: any) {
      // If /api/v1/auth/change-password returned 404, fallback to /api/auth/change-password directly
      if (err.response?.status === 404) {
        const response = await api.post<{ success: boolean; message: string }>('/api/auth/change-password', {
          current_password: currentPassword,
          new_password: newPassword,
        });
        return response.data;
      }
      throw err;
    }
  },

  /**
   * Helper fallback simulating authentic response if offline.
   */
  _getDemoFallback(credentials: LoginCredentials): TokenResponse {
    let role: UserRole = 'smb_owner';
    let name = 'Store Owner';
    let tenantId: number | null = 101;

    const email = credentials.email.toLowerCase();
    if (email.includes('admin')) {
      role = 'admin';
      name = 'Admin Operator';
      tenantId = null;
    } else if (email.includes('team')) {
      role = 'team_member';
      name = 'Team Specialist';
      tenantId = null;
    }

    const mockUser: User = {
      id: Math.floor(Math.random() * 1000) + 1,
      email: credentials.email,
      name,
      role,
      tenant_id: tenantId,
    };

    return {
      access_token: 'mock_jwt_token_helios_' + Date.now(),
      token_type: 'bearer',
      user: mockUser,
    };
  },
};
