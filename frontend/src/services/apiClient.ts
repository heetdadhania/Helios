import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Standard API Client with JWT bearer token and tenant isolation header.
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor: attach JWT token and tenant context
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('helios_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    const tenantId = localStorage.getItem('helios_tenant_id');
    if (tenantId && config.headers) {
      config.headers['X-Tenant-ID'] = tenantId;
    }

    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor: handle 401 unauthorized & format error responses
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('helios_token');
      localStorage.removeItem('helios_user');
      localStorage.removeItem('helios_tenant_id');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Dedicated Non-JWT API Push Client for Module 5.
 * Authenticates exclusively via the X-Helios-Api-Key header without sending Bearer tokens.
 */
export function createApiKeyClient(apiKey: string): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    headers: {
      'Content-Type': 'application/json',
      'X-Helios-Api-Key': apiKey.trim(),
    },
    timeout: 30000,
  });

  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      // Do not redirect to login on 401 for programmatic API key calls
      return Promise.reject(error);
    }
  );

  return client;
}

export default apiClient;
