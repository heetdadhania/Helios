import React, { useEffect, useState } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Loader2,
  RefreshCw,
  CheckCheck,
} from 'lucide-react';
import { notificationService } from '@/services/notificationService';
import { Notification } from '@/types/notification';
import { formatDateTimeIN } from '@/utils/currency';

export const ClientNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationService.getNotifications({ limit: 50 });
      setNotifications(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAsRead = async (id: number) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.notification_id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationService.markAllAsRead(notifications);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err);
    }
  };

  const renderIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('fail') || t.includes('restart') || t.includes('error')) {
      return <AlertTriangle className="w-4 h-4 text-rose-500" />;
    }
    if (t.includes('success') || t.includes('ready')) {
      return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
    }
    if (t.includes('confirm') || t.includes('pending')) {
      return <Clock className="w-4 h-4 text-amber-500" />;
    }
    return <Info className="w-4 h-4 text-blue-500" />;
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-helios-accent-blue/10 text-helios-accent-blue">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Notifications & Pipeline Alerts
            </h1>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              System alerts, batch processing statuses, and operational notifications.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={handleMarkAllAsRead}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 text-helios-text-primary-light dark:text-helios-text-primary-dark transition"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              <span>Mark all as read</span>
            </button>
          )}
          <button
            type="button"
            onClick={fetchNotifications}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error state */}
      {!loading && error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchNotifications}
            className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-600 text-white hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Notifications List */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs">
        {loading && (
          <div className="p-8 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-helios-accent-blue mb-2" />
            <p className="text-xs">Loading notifications...</p>
          </div>
        )}

        {!loading && !error && notifications.length === 0 && (
          <div className="p-8 text-center border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl">
            <Bell className="w-8 h-8 mx-auto text-gray-400 mb-2" />
            <p className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No notifications yet.
            </p>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
              You will receive alerts here when batches complete, need confirmation, or encounter errors.
            </p>
          </div>
        )}

        {!loading && !error && notifications.length > 0 && (
          <div className="space-y-3">
            {notifications.map((n) => (
              <div
                key={n.notification_id}
                onClick={() => !n.is_read && handleMarkAsRead(n.notification_id)}
                className={`p-4 rounded-xl border transition cursor-pointer flex items-start gap-3 ${
                  n.is_read
                    ? 'border-helios-border-light dark:border-helios-border-dark bg-transparent opacity-75'
                    : 'border-blue-200 dark:border-blue-800 bg-blue-50/40 dark:bg-blue-950/20'
                }`}
              >
                <div className="p-2 rounded-lg bg-black/5 dark:bg-white/5 shrink-0 mt-0.5">
                  {renderIcon(n.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark capitalize">
                      {n.type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[11px] text-gray-400">
                      {n.created_at ? formatDateTimeIN(n.created_at) : ''}
                    </span>
                  </div>
                  <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    {n.message}
                  </p>
                </div>
                {!n.is_read && (
                  <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0 mt-1.5" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
