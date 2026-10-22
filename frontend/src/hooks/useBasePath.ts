import { useAuth } from './useAuth';

export const useBasePath = (): string => {
  const { user } = useAuth();
  return user?.role === 'team_member' ? '/team' : '/admin';
};

export default useBasePath;
