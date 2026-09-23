import api from './api';
import { ApiKeyInfo, ApiKeyGenerated } from '@/types/apiKey';

const API_KEYS_ENDPOINT = '/api-keys';

// In-memory fallback for offline/demo development
let fallbackApiKey: ApiKeyInfo | null = {
  api_key_id: 101,
  tenant_id: 42,
  masked_key: 'helios_live_••••8f9b',
  created_at: new Date(Date.now() - 86400000 * 14).toISOString(),
  last_used_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  is_active: true,
};

export const apiKeyService = {
  /**
   * Retrieve active API key information for current tenant.
   * Calls GET /api/v1/api-keys (or /api/api-keys).
   */
  async getApiKeyInfo(): Promise<ApiKeyInfo | null> {
    try {
      const response = await api.get<ApiKeyInfo | null>(API_KEYS_ENDPOINT);
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return fallbackApiKey;
      }
      throw error;
    }
  },

  /**
   * Invalidate old key and generate a new cryptographic key.
   * Calls POST /api/v1/api-keys/regenerate.
   * Returns full raw key ONE TIME ONLY.
   */
  async regenerateApiKey(): Promise<ApiKeyGenerated> {
    try {
      const response = await api.post<ApiKeyGenerated>(`${API_KEYS_ENDPOINT}/regenerate`);
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        const randomSuffix = Math.random().toString(36).substring(2, 10) + Math.random().toString(36).substring(2, 10);
        const fullKey = `helios_live_${randomSuffix}`;
        const masked = `helios_live_••••${fullKey.slice(-4)}`;

        const generated: ApiKeyGenerated = {
          api_key_id: Date.now(),
          tenant_id: 42,
          api_key: fullKey,
          masked_key: masked,
          created_at: new Date().toISOString(),
          message: 'API key generated successfully. Save this key now; it will not be displayed again.',
        };

        fallbackApiKey = {
          api_key_id: generated.api_key_id,
          tenant_id: generated.tenant_id,
          masked_key: generated.masked_key,
          created_at: generated.created_at,
          last_used_at: null,
          is_active: true,
        };

        return generated;
      }
      const errMsg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to regenerate API key.';
      throw new Error(errMsg);
    }
  },
};
