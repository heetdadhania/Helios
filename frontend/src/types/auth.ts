export type UserRole = 'smb_owner' | 'team_member' | 'admin';

export interface User {
  id: number | string;
  email: string;
  name: string;
  role: UserRole;
  tenant_id?: number | null;
  avatarUrl?: string;
  must_change_password?: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => void;
  updateUser: (updated: Partial<User>) => void;
}
