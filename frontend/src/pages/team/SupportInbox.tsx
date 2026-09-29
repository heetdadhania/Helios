import React, { useEffect, useState, useMemo } from 'react';
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
  Flag,
  AlertTriangle,
} from 'lucide-react';
import { supportService } from '@/services/supportService';
import { SupportMessage } from '@/types/support';

export const SupportInbox: React.FC = () => {
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'flagged' | 'smb'>('all');
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

  // Filter messages by source filter
  const displayedMessages = useMemo(() => {
    if (sourceFilter === 'flagged') {
      return messages.filter((m) => m.message_source === 'team_member');
    }
    if (sourceFilter === 'smb') {
      return messages.filter((m) => m.message_source !== 'team_member');
    }
    return messages;
  }, [messages, sourceFilter]);

  const flaggedCount = useMemo(() => {
    return messages.filter((m) => m.message_source === 'team_member' && m.status === 'open').length;
  }, [messages]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Support & Escalations Inbox</h1>
            {flaggedCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                {flaggedCount} Open Escalation{flaggedCount === 1 ? '' : 's'}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Unified inbox for client status requests and Team Member flagged escalations.
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
      <div className="bg-white dark:bg-gray-850 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Status:</span>
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

          {/* Type Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Source:</span>
            <div className="inline-flex rounded-lg p-0.5 bg-gray-100 dark:bg-gray-800">
              <button
                type="button"
                onClick={() => setSourceFilter('all')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  sourceFilter === 'all'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                All Sources
              </button>
              <button
                type="button"
                onClick={() => setSourceFilter('flagged')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  sourceFilter === 'flagged'
                    ? 'bg-rose-500 text-white shadow-xs'
                    : 'text-rose-600 dark:text-rose-400 hover:bg-rose-500/10'
                }`}
              >
                <Flag className="w-3 h-3 fill-current" />
                <span>Flagged Escalations</span>
              </button>
              <button
                type="button"
                onClick={() => setSourceFilter('smb')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  sourceFilter === 'smb'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-xs'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                SMB Requests
              </button>
            </div>
          </div>
        </div>

        <div className="text-xs text-gray-400">
          Showing {displayedMessages.length} message{displayedMessages.length === 1 ? '' : 's'}
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
      ) : displayedMessages.length === 0 ? (
        <div className="p-16 text-center bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-800">
          <Inbox className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" />
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">No messages match filter</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {sourceFilter === 'flagged'
              ? 'No Team Member flagged escalations found.'
              : statusFilter === 'all'
              ? 'Your inbox is clear! Any inquiries or flags will appear here.'
              : `No messages currently marked as '${statusFilter}'.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayedMessages.map((item) => {
            const isOpen = item.status === 'open';
            const isFlagged = item.message_source === 'team_member';

            return (
              <div
                key={item.message_id}
                className={`p-5 rounded-xl bg-white dark:bg-gray-850 border transition shadow-xs ${
                  isFlagged
                    ? isOpen
                      ? 'border-rose-400 dark:border-rose-800/80 ring-2 ring-rose-500/15 bg-rose-500/[0.02]'
                      : 'border-rose-200 dark:border-rose-900/40 opacity-80 hover:opacity-100'
                    : isOpen
                    ? 'border-blue-200 dark:border-blue-900/60 ring-1 ring-blue-500/10'
                    : 'border-gray-200 dark:border-gray-800 opacity-80 hover:opacity-100'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Message Metadata */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Flagged Escalation vs SMB Inquiry Badge */}
                      {isFlagged ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 shadow-xs">
                          <Flag className="w-3 h-3 text-rose-500 fill-current" />
                          <span>Flagged Escalation</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                          <span>SMB Request</span>
                        </span>
                      )}

                      {/* Tenant tag */}
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200">
                        <Building2 className="w-3 h-3 text-gray-500" />
                        {item.tenant_name || `Tenant #${item.tenant_id}`}
                      </span>

                      {/* Sender */}
                      <span className="inline-flex items-center gap-1 text-xs">
                        <User className="w-3 h-3 text-gray-400" />
                        {isFlagged ? (
                          <strong className="text-rose-600 dark:text-rose-400 font-semibold">
                            {item.from_user_name || 'Team Member'} (Ops)
                          </strong>
                        ) : (
                          <span className="text-gray-600 dark:text-gray-300">
                            {item.from_user_name ? `${item.from_user_name} (SMB Owner)` : 'SMB Owner'}
                          </span>
                        )}
                      </span>

                      {/* Recipient info */}
                      {item.to_user_name && (
                        <span className="text-xs text-gray-400">
                          → Recipient: <strong className="text-gray-600 dark:text-gray-300 font-medium">{item.to_user_name}</strong>
                        </span>
                      )}

                      {/* Status badge */}
                      {isOpen ? (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ml-auto md:ml-0 ${
                          isFlagged
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-300 dark:border-rose-800 font-bold'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                        }`}>
                          <Clock className="w-3 h-3" />
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
                    <div className={`p-3.5 rounded-lg border text-sm whitespace-pre-wrap leading-relaxed ${
                      isFlagged
                        ? 'bg-rose-500/[0.04] dark:bg-rose-950/20 border-rose-500/20 text-gray-900 dark:text-gray-100'
                        : 'bg-gray-50 dark:bg-gray-900 border-gray-100 dark:border-gray-800 text-gray-900 dark:text-gray-100'
                    }`}>
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
                        className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg text-white transition shadow-xs disabled:opacity-50 ${
                          isFlagged
                            ? 'bg-rose-600 hover:bg-rose-700'
                            : 'bg-emerald-600 hover:bg-emerald-700'
                        }`}
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
