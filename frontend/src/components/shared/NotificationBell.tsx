import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  UploadCloud,
  RotateCcw,
  Info,
  CheckCheck,
  RefreshCw,
} from 'lucide-react';
import { Notification } from '@/types/notification';
import { notificationService } from '@/services/notificationService';

const POLL_INTERVAL_MS = 30000;

/**
 * Format timestamp into relative time string ("Just now", "5m ago", "2h ago", "3d ago")
 */
function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return 'Just now';

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Recently';

    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 0) return 'Just now';
    if (diffInSeconds < 45) return 'Just now';
    if (diffInSeconds < 3600) {
      const minutes = Math.max(1, Math.floor(diffInSeconds / 60));
      return `${minutes}m ago`;
    }
    if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours}h ago`;
    }
    if (diffInSeconds < 604800) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days}d ago`;
    }

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'Recently';
  }
}

/**
 * Render appropriate category icon based on notification type
 */
function NotificationIcon({ type }: { type: string }) {
  const normalized = type.toLowerCase();

  switch (normalized) {
    case 'dashboard_ready':
    case 'pipeline_success':
      return (
        <div className="p-1.5 rounded-full bg-emerald-500/10 text-emerald-500 flex-shrink-0">
          <CheckCircle2 className="w-4 h-4" />
        </div>
      );
    case 'pipeline_failed':
    case 'error':
      return (
        <div className="p-1.5 rounded-full bg-red-500/10 text-red-500 flex-shrink-0">
          <AlertCircle className="w-4 h-4" />
        </div>
      );
    case 'restart_required':
      return (
        <div className="p-1.5 rounded-full bg-amber-500/10 text-amber-500 flex-shrink-0">
          <RotateCcw className="w-4 h-4" />
        </div>
      );
    case 'warning':
    case 'approval_required':
      return (
        <div className="p-1.5 rounded-full bg-amber-500/10 text-amber-500 flex-shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </div>
      );
    case 'upload_received':
      return (
        <div className="p-1.5 rounded-full bg-blue-500/10 text-blue-500 flex-shrink-0">
          <UploadCloud className="w-4 h-4" />
        </div>
      );
    default:
      return (
        <div className="p-1.5 rounded-full bg-helios-accent-blue/10 text-helios-accent-blue flex-shrink-0">
          <Info className="w-4 h-4" />
        </div>
      );
  }
}

export const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterUnreadOnly, setFilterUnreadOnly] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch notifications from server
  const fetchNotifications = useCallback(async () => {
    try {
      const data = await notificationService.getNotifications({ limit: 40 });
      setNotifications(data);
    } catch {
      // Silently catch network/polling errors so UI remains stable
    }
  }, []);

  // Initial load and 30-second polling
  useEffect(() => {
    fetchNotifications();

    const intervalId = setInterval(() => {
      fetchNotifications();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [fetchNotifications]);

  // Close dropdown on outside click or escape
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // Handle marking a single notification as read
  const handleNotificationClick = async (notification: Notification) => {
    if (notification.is_read) return;

    // Optimistically mark as read in local state
    setNotifications((prev) =>
      prev.map((item) =>
        item.notification_id === notification.notification_id
          ? { ...item, is_read: true }
          : item
      )
    );

    try {
      await notificationService.markAsRead(notification.notification_id);
    } catch {
      // If server failed, revert in background by re-fetching
      fetchNotifications();
    }
  };

  // Handle mark all as read
  const handleMarkAllAsRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    if (unread.length === 0) return;

    // Optimistic update
    setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));

    try {
      setIsLoading(true);
      await notificationService.markAllAsRead(unread);
    } catch {
      fetchNotifications();
    } finally {
      setIsLoading(false);
    }
  };

  const displayedNotifications = filterUnreadOnly
    ? notifications.filter((n) => !n.is_read)
    : notifications;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 rounded-control text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors focus:outline-none focus:ring-1 focus:ring-helios-accent-blue"
        aria-label="Notifications"
        aria-expanded={isOpen}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-helios-accent-blue rounded-full ring-2 ring-helios-sidebar-light dark:ring-helios-sidebar-dark transition-transform animate-in fade-in zoom-in">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          role="region"
          aria-label="Notification list"
          className="absolute right-0 mt-2 w-80 sm:w-96 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-soft z-50 overflow-hidden flex flex-col transition-colors duration-200"
        >
          {/* Header */}
          <div className="p-3.5 border-b border-helios-border-light dark:border-helios-border-dark flex items-center justify-between bg-helios-sidebar-light/50 dark:bg-helios-sidebar-dark/50">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                Notifications
              </h2>
              {unreadCount > 0 && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-helios-accent-blue/15 text-helios-accent-blue">
                  {unreadCount} unread
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllAsRead}
                  disabled={isLoading}
                  className="flex items-center gap-1 text-[11px] font-medium text-helios-accent-blue hover:text-blue-600 dark:hover:text-blue-400 p-1 rounded hover:bg-helios-accent-blue/10 transition-colors disabled:opacity-50"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span>Mark all read</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => fetchNotifications()}
                className="p-1 rounded text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                title="Refresh notifications"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-helios-border-light dark:border-helios-border-dark text-xs px-3 py-1.5 bg-black/[0.02] dark:bg-white/[0.02] gap-2">
            <button
              type="button"
              onClick={() => setFilterUnreadOnly(false)}
              className={`px-2.5 py-1 rounded-control transition-colors ${
                !filterUnreadOnly
                  ? 'bg-helios-accent-blue text-white font-medium'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterUnreadOnly(true)}
              className={`px-2.5 py-1 rounded-control transition-colors ${
                filterUnreadOnly
                  ? 'bg-helios-accent-blue text-white font-medium'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              Unread ({unreadCount})
            </button>
          </div>

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-helios-border-light dark:divide-helios-border-dark">
            {displayedNotifications.length === 0 ? (
              <div className="py-10 px-4 text-center">
                <Bell className="w-8 h-8 mx-auto text-helios-text-secondary-light/40 dark:text-helios-text-secondary-dark/40 mb-2 stroke-1" />
                <p className="text-xs font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {filterUnreadOnly ? 'No unread notifications' : 'No notifications yet'}
                </p>
                <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
                  {filterUnreadOnly
                    ? "You've caught up on everything!"
                    : "Operational and pipeline updates will appear here."}
                </p>
              </div>
            ) : (
              displayedNotifications.map((notification) => (
                <div
                  key={notification.notification_id}
                  onClick={() => handleNotificationClick(notification)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      handleNotificationClick(notification);
                    }
                  }}
                  className={`w-full text-left p-3.5 flex items-start gap-3 transition-colors cursor-pointer select-none ${
                    !notification.is_read
                      ? 'bg-helios-accent-blue/[0.04] dark:bg-helios-accent-blue/[0.08] hover:bg-helios-accent-blue/[0.08] dark:hover:bg-helios-accent-blue/[0.12]'
                      : 'hover:bg-black/[0.03] dark:hover:bg-white/[0.03]'
                  }`}
                >
                  <NotificationIcon type={notification.type} />

                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-xs leading-snug line-clamp-2 ${
                        !notification.is_read
                          ? 'font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark'
                          : 'font-normal text-helios-text-secondary-light dark:text-helios-text-secondary-dark'
                      }`}
                    >
                      {notification.message}
                    </p>

                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        {formatRelativeTime(notification.created_at)}
                      </span>
                      {notification.type && (
                        <span className="text-[9px] uppercase tracking-wider font-semibold text-helios-text-secondary-light/80 dark:text-helios-text-secondary-dark/80">
                          • {notification.type.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                  </div>

                  {!notification.is_read && (
                    <span
                      className="w-2 h-2 mt-1.5 rounded-full bg-helios-accent-blue flex-shrink-0"
                      title="Unread"
                    />
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
