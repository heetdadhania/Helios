import React, { useEffect, useState } from 'react';
import {
  Inbox,
  CheckCircle2,
  Clock,
  RefreshCw,
  Building2,
  User,
  Filter,
  CheckCheck,
  AlertCircle,
} from 'lucide-react';
import { supportService } from '@/services/supportService';
import { SupportMessage } from '@/types/support';

export const SupportInbox: React.FC = () => {
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  const fetchMessages = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await supportService.getMessages(statusFilter);
      setMessages(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to retrieve support inquiries.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [statusFilter]);

  const handleResolve = async (messageId: number) => {
    setResolvingId(messageId);
    try {
      await supportService.resolveMessage(messageId);
      // Update local state
      setMessages((prev) =>
        prev.map((m) =>
          m.message_id === messageId
            ? { ...m, status: 'resolved', resolved_at: new Date().toISOString() }
            : m
        )
      );
    } catch (err: any) {
      setError(err?.message || `Failed to mark message #${messageId} as resolved.`);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Support & Update Requests</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Incoming inquiries and status check requests submitted by tenant owners.
          </p>
        </div>
        <button
          onClick={fetchMessages}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-750 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white dark:bg-gray-850 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Filter State:</span>
          <div className="inline-flex rounded-lg p-0.5 bg-gray-100 dark:bg-gray-800">
            {(['all', 'open', 'resolved'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md capitalize transition ${
                  statusFilter === tab
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="text-xs text-gray-400">
          Showing {messages.length} message{messages.length === 1 ? '' : 's'}
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 flex items-center gap-2 text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Message List */}
      {loading ? (
        <div className="p-16 text-center text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-800">
          <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-3 text-blue-600" />
          Loading inbox messages...
        </div>
      ) : messages.length === 0 ? (
        <div className="p-16 text-center bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-800">
          <Inbox className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">No support messages</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {statusFilter === 'all'
              ? 'Your inbox is clear! Any inquiries from tenant owners will appear here.'
              : `No messages currently marked as '${statusFilter}'.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((item) => {
            const isOpen = item.status === 'open';

            return (
              <div
                key={item.message_id}
                className={`p-5 rounded-xl bg-white dark:bg-gray-850 border transition shadow-xs ${
                  isOpen
                    ? 'border-blue-200 dark:border-blue-900/60 ring-1 ring-blue-500/10'
                    : 'border-gray-200 dark:border-gray-800 opacity-80 hover:opacity-100'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Message Metadata */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Tenant tag */}
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200">
                        <Building2 className="w-3 h-3 text-gray-500" />
                        {item.tenant_name || `Tenant #${item.tenant_id}`}
                      </span>

                      {/* Sender */}
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                        <User className="w-3 h-3 text-gray-400" />
                        {item.from_user_name ? `${item.from_user_name} (SMB Owner)` : 'SMB Owner'}
                      </span>

                      {/* Recipient info */}
                      {item.to_user_name && (
                        <span className="text-xs text-gray-400">
                          → Assigned to: <strong className="text-gray-600 dark:text-gray-300 font-medium">{item.to_user_name}</strong>
                        </span>
                      )}

                      {/* Status badge */}
                      {isOpen ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-300 dark:border-amber-800 ml-auto md:ml-0">
                          <Clock className="w-3 h-3 text-amber-600" />
                          Open
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 ml-auto md:ml-0">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Resolved
                        </span>
                      )}
                    </div>

                    {/* Message Body */}
                    <div className="p-3.5 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed">
                      {item.message}
                    </div>

                    {/* Timestamps */}
                    <div className="text-xs text-gray-400 flex flex-wrap gap-4 pt-1">
                      <span>Submitted: {new Date(item.created_at).toLocaleString()}</span>
                      {item.resolved_at && (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          Resolved: {new Date(item.resolved_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Button */}
                  <div className="shrink-0 self-end md:self-center">
                    {isOpen ? (
                      <button
                        type="button"
                        onClick={() => handleResolve(item.message_id)}
                        disabled={resolvingId === item.message_id}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition shadow-xs"
                      >
                        <CheckCheck className={`w-3.5 h-3.5 ${resolvingId === item.message_id ? 'animate-spin' : ''}`} />
                        <span>{resolvingId === item.message_id ? 'Resolving...' : 'Mark Resolved'}</span>
                      </button>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-3 py-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Completed
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SupportInbox;
