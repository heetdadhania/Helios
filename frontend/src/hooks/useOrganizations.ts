import { useState, useEffect, useCallback } from 'react';
import { Tenant } from '@/types/admin';
import { adminService } from '@/services/adminService';

export interface UseOrganizationsReturn {
  organizations: Tenant[];
  tenants: Tenant[];
  isLoading: boolean;
  error: string | null;
  selectedOrgId: string;
  setSelectedOrgId: (id: string) => void;
  refetch: () => Promise<void>;
}

export function useOrganizations(): UseOrganizationsReturn {
  const [organizations, setOrganizations] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');

  const fetchOrganizations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminService.getTenants();
      setOrganizations(data);
      if (data.length === 1) {
        // Preselect the organization if there is only one
        setSelectedOrgId(String(data[0].tenant_id));
      } else if (data.length > 1) {
        setSelectedOrgId((prev) => {
          if (prev && data.some((t) => String(t.tenant_id) === String(prev))) {
            return prev;
          }
          return '';
        });
      } else {
        setSelectedOrgId('');
      }
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.detail || err?.message || 'Failed to load organizations.';
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  return {
    organizations,
    tenants: organizations,
    isLoading,
    error,
    selectedOrgId,
    setSelectedOrgId,
    refetch: fetchOrganizations,
  };
}
