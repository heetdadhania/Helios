import api from './api';
import { ApiKeyInfo, ApiKeyGenerated } from '@/types/apiKey';

const API_KEYS_ENDPOINT = '/api-keys';

export const apiKeyService = {
  /**
   * Retrieve active API key information for current tenant.
   * Calls GET /api/v1/api-keys (or /api/api-keys).
   */
  async getApiKeyInfo(): Promise<ApiKeyInfo | null> {
    const response = await api.get<ApiKeyInfo | null>(API_KEYS_ENDPOINT);
    return response.data;
  },

  /**
   * Invalidate old key and generate a new cryptographic key.
   * Calls POST /api/v1/api-keys/regenerate.
   * Returns full raw key ONE TIME ONLY.
   */
  async regenerateApiKey(): Promise<ApiKeyGenerated> {
    const response = await api.post<ApiKeyGenerated>(`${API_KEYS_ENDPOINT}/regenerate`);
    return response.data;
  },
};
