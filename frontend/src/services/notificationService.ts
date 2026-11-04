import api from './api';
import {
  Notification,
  NotificationReadResponse,
  NotificationFilterParams,
} from '@/types/notification';
import { PaginatedResponse } from '@/types/pagination';

export const notificationService = {
  /**
   * Fetch notifications scoped to the current user and tenant with server-side pagination.
   */
  async getNotifications(
    params?: NotificationFilterParams & { page?: number; pageSize?: number }
  ): Promise<PaginatedResponse<Notification>> {
    const page = params?.page ?? 1;
    const pageSize = params?.pageSize ?? (params?.limit ?? 20);
    const response = await api.get<PaginatedResponse<Notification>>('/notifications', {
      params: {
        unread_only: params?.unread_only,
        page,
        page_size: pageSize,
      },
    });
    return response.data;
  },

  /**
   * Mark a specific notification as read.
   */
  async markAsRead(notificationId: number): Promise<NotificationReadResponse> {
    const response = await api.post<NotificationReadResponse>(
      `/notifications/${notificationId}/read`
    );
    return response.data;
  },

  /**
   * Mark all unread notifications in a list as read.
   */
  async markAllAsRead(notifications: Notification[]): Promise<void> {
    const unread = notifications.filter((n) => !n.is_read);
    await Promise.allSettled(
      unread.map((n) => api.post(`/notifications/${n.notification_id}/read`))
    );
  },
};
