import api from './api';
import {
  SupportMessage,
  SupportMessageCreatePayload,
  SupportFlagPayload,
  SupportMessageResolveResponse,
} from '@/types/support';

export const supportService = {
  /**
   * Send a support or update request from SMB Owner to assigned Team Member / Admin.
   */
  async sendMessage(message: string): Promise<SupportMessage> {
    try {
      const payload: SupportMessageCreatePayload = { message };
      const response = await api.post<SupportMessage>('/support/messages', payload);
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        // Fallback for offline/demo testing
        return {
          message_id: Date.now(),
          tenant_id: 1,
          from_user_id: 1,
          to_user_id: 2,
          message,
          message_source: 'smb_owner',
          status: 'open',
          created_at: new Date().toISOString(),
          resolved_at: null,
        };
      }
      const errMsg = error.response?.data?.detail || 'Failed to send support request.';
      throw new Error(errMsg);
    }
  },

  /**
   * Flag an issue or pipeline failure directly to Admin (Team Member / Admin action).
   */
  async flagForAdmin(payload: SupportFlagPayload): Promise<SupportMessage> {
    try {
      const response = await api.post<SupportMessage>('/support/flag', payload);
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return {
          message_id: Date.now(),
          tenant_id: payload.tenant_id,
          from_user_id: 1,
          to_user_id: 2,
          message: payload.batch_id ? `[Batch: ${payload.batch_id}] ${payload.message}` : payload.message,
          message_source: 'team_member',
          batch_id: payload.batch_id || null,
          status: 'open',
          created_at: new Date().toISOString(),
          resolved_at: null,
        };
      }
      const errMsg = error.response?.data?.detail || 'Failed to submit escalation flag to Admin.';
      throw new Error(errMsg);
    }
  },

  /**
   * Retrieve support messages routed to caller (Team Member) or all (Admin).
   */
  async getMessages(status?: string): Promise<SupportMessage[]> {
    try {
      const params: Record<string, string> = {};
      if (status && status !== 'all') {
        params.status = status;
      }
      const response = await api.get<SupportMessage[]>('/support/messages', { params });
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return [
          {
            message_id: 101,
            tenant_id: 1,
            tenant_name: 'Summit Athletics',
            from_user_id: 10,
            from_user_name: 'Alex Owner',
            to_user_id: 20,
            to_user_name: 'Alice Support',
            message: 'Hello! Can you please verify if our Q3 sales CSV has completed processing?',
            status: 'open',
            created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
            resolved_at: null,
          },
          {
            message_id: 102,
            tenant_id: 2,
            tenant_name: 'Nordic Outfitters',
            from_user_id: 11,
            from_user_name: 'Elena Hansen',
            to_user_id: 20,
            to_user_name: 'Alice Support',
            message: 'We updated our PostgreSQL connector credentials. Please trigger a sync when possible.',
            status: 'resolved',
            created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
            resolved_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
          },
        ];
      }
      const errMsg = error.response?.data?.detail || 'Failed to fetch support messages.';
      throw new Error(errMsg);
    }
  },

  /**
   * Mark support message as resolved (Team Member / Admin).
   */
  async resolveMessage(messageId: number): Promise<SupportMessageResolveResponse> {
    try {
      const response = await api.post<SupportMessageResolveResponse>(
        `/support/messages/${messageId}/resolve`
      );
      return response.data;
    } catch (error: any) {
      if (!error.response || error.code === 'ERR_NETWORK') {
        return {
          success: true,
          message: 'Support message marked as resolved.',
          message_id: messageId,
          status: 'resolved',
          resolved_at: new Date().toISOString(),
        };
      }
      const errMsg = error.response?.data?.detail || 'Failed to resolve support message.';
      throw new Error(errMsg);
    }
  },
};
