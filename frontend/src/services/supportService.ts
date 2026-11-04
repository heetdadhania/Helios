import api from './api';
import {
  SupportMessage,
  SupportMessageCreatePayload,
  SupportFlagPayload,
  SupportMessageResolveResponse,
} from '@/types/support';
import { PaginatedResponse } from '@/types/pagination';

export const supportService = {
  /**
   * Send a support or update request from SMB Owner to assigned Team Member / Admin.
   */
  async sendMessage(message: string): Promise<SupportMessage> {
    const payload: SupportMessageCreatePayload = { message };
    const response = await api.post<SupportMessage>('/support/messages', payload);
    return response.data;
  },

  /**
   * Flag an issue or pipeline failure directly to Admin (Team Member / Admin action).
   */
  async flagForAdmin(payload: SupportFlagPayload): Promise<SupportMessage> {
    const response = await api.post<SupportMessage>('/support/flag', payload);
    return response.data;
  },

  /**
   * Retrieve support messages routed to caller (Team Member) or all (Admin) with server-side pagination.
   */
  async getMessages(
    status?: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<SupportMessage>> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (status && status !== 'all') {
      params.status = status;
    }
    const response = await api.get<PaginatedResponse<SupportMessage>>('/support/messages', { params });
    return response.data;
  },

  /**
   * Mark support message as resolved (Team Member / Admin).
   */
  async resolveMessage(messageId: number): Promise<SupportMessageResolveResponse> {
    const response = await api.post<SupportMessageResolveResponse>(
      `/support/messages/${messageId}/resolve`
    );
    return response.data;
  },
};
