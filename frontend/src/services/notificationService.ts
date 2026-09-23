import api from './api';
import {
  Notification,
  NotificationReadResponse,
  NotificationFilterParams,
} from '@/types/notification';

export const notificationService = {
  /**
   * Fetch notifications scoped to the current user and tenant.
   */
  async getNotifications(params?: NotificationFilterParams): Promise<Notification[]> {
    const response = await api.get<Notification[]>('/notifications', {
      params: {
        unread_only: params?.unread_only,
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0,
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
