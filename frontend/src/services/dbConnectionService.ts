import api from './api';
import {
  DbConnectionCreate,
  DbConnectionOut,
  DbConnectionTestResult,
  DbConnectionSyncResponse,
} from '@/types/dbConnection';

const DB_CONNECTIONS_ENDPOINT = '/db-connections';

export const dbConnectionService = {
  /**
   * Test external database connectivity using provided credentials.
   * Calls POST /api/v1/db-connections/test (or /api/db-connections/test).
   */
  async testConnection(params: DbConnectionCreate): Promise<DbConnectionTestResult> {
    const response = await api.post<DbConnectionTestResult>(
      `${DB_CONNECTIONS_ENDPOINT}/test`,
      params
    );
    return response.data;
  },

  /**
   * Save database connection. Sends credentials to Databricks Secrets and stores metadata.
   * Calls POST /api/v1/db-connections.
   */
  async saveConnection(params: DbConnectionCreate): Promise<DbConnectionOut> {
    const response = await api.post<DbConnectionOut>(
      DB_CONNECTIONS_ENDPOINT,
      params
    );
    return response.data;
  },

  /**
   * Retrieve list of saved database connections for current tenant.
   * Calls GET /api/v1/db-connections.
   */
  async listConnections(): Promise<DbConnectionOut[]> {
    const response = await api.get<DbConnectionOut[]>(DB_CONNECTIONS_ENDPOINT);
    return response.data;
  },

  /**
   * Trigger on-demand sync for a saved database connection.
   * Calls POST /api/v1/db-connections/{connection_id}/sync.
   */
  async syncNow(connectionId: number): Promise<DbConnectionSyncResponse> {
    const response = await api.post<DbConnectionSyncResponse>(
      `${DB_CONNECTIONS_ENDPOINT}/${connectionId}/sync`
    );
    return response.data;
  },
};
