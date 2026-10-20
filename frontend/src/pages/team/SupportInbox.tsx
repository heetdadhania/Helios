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
  RotateCcw,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { supportService } from '@/services/supportService';
import { SupportMessage } from '@/types/support';
import { formatDateTimeIN } from '@/utils/currency';

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
      // Update local state smoothly
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
      return messages.filter(
        (m) => (m.message_source || '').toLowerCase().trim() === 'team_member'
      );
    }
    if (sourceFilter === 'smb') {
      return messages.filter(
        (m) => (m.message_source || '').toLowerCase().trim() !== 'team_member'
      );
    }
    return messages;
  }, [messages, sourceFilter]);

  const flaggedCount = useMemo(() => {
    return messages.filter(
      (m) =>
        (m.message_source || '').toLowerCase().trim() === 'team_member' &&
        m.status === 'open'
    ).length;
  }, [messages]);

  const openCount = useMemo(() => {
    return messages.filter((m) => m.status === 'open').length;
  }, [messages]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Support & Escalations Inbox
            </h1>
            {flaggedCount > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30 animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                <span>{flaggedCount} Open Escalation{flaggedCount === 1 ? '' : 's'}</span>
              </span>
            )}
            {openCount > 0 && flaggedCount === 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                <Clock className="w-3.5 h-3.5 text-blue-500" />
                <span>{openCount} Open Item{openCount === 1 ? '' : 's'}</span>
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Unified inbox for client status inquiries and Team Member flagged escalations.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchMessages}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50 self-start sm:self-auto shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-helios-accent-blue' : ''}`} />
          <span>Refresh Inbox</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-helios-card-light dark:bg-helios-card-dark p-4 rounded-xl shadow-sm border border-helios-border-light dark:border-helios-border-dark flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Status Filter Tabs */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider">
              Status:
            </span>
            <div className="inline-flex rounded-lg p-0.5 bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark">
              {(['all', 'open', 'resolved'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setStatusFilter(tab)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md capitalize transition ${
                    statusFilter === tab
                      ? 'bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark shadow-xs'
                      : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Source Filter Tabs */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-helios-text-secondary-light dark:text-helios-text-secondary-dark uppercase tracking-wider">
              Source:
            </span>
            <div className="inline-flex rounded-lg p-0.5 bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark">
              <button
                type="button"
                onClick={() => setSourceFilter('all')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                  sourceFilter === 'all'
                    ? 'bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark shadow-xs'
                    : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
                }`}
              >
                All Sources
              </button>
              <button
                type="button"
                onClick={() => setSourceFilter('flagged')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                  sourceFilter === 'flagged'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'text-rose-600 dark:text-rose-400 hover:bg-rose-500/10'
                }`}
              >
                <Flag className="w-3 h-3 fill-current" />
                <span>Flagged Escalations</span>
              </button>
              <button
                type="button"
                onClick={() => setSourceFilter('smb')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                  sourceFilter === 'smb'
                    ? 'bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark shadow-xs'
                    : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
                }`}
              >
                Organization Inquiries
              </button>
            </div>
          </div>
        </div>

        <div className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-medium">
          Showing {displayedMessages.length} message{displayedMessages.length === 1 ? '' : 's'}
        </div>
      </div>

      {/* Persistent / Action Error Alert Banner (if error occurred during resolve) */}
      {error && messages.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between text-rose-600 dark:text-rose-400 text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchMessages}
            className="inline-flex items-center gap-1 text-xs font-semibold underline hover:no-underline ml-3"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        /* Loading Skeleton matching the message card grid layout */
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-5 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm animate-pulse space-y-4"
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-3 flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <div className="h-5 w-28 bg-slate-200 dark:bg-slate-800 rounded-full" />
                    <div className="h-5 w-32 bg-slate-200 dark:bg-slate-800 rounded-md" />
                    <div className="h-5 w-24 bg-slate-200 dark:bg-slate-800 rounded-md" />
                    <div className="h-5 w-16 bg-slate-200 dark:bg-slate-800 rounded-full ml-auto md:ml-0" />
                  </div>
                  <div className="p-3.5 rounded-lg bg-black/5 dark:bg-white/5 space-y-2">
                    <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-800 rounded" />
                    <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-800 rounded" />
                  </div>
                  <div className="h-3 w-40 bg-slate-200 dark:bg-slate-800 rounded" />
                </div>
                <div className="h-9 w-28 bg-slate-200 dark:bg-slate-800 rounded-lg shrink-0 self-end md:self-center" />
              </div>
            </div>
          ))}
        </div>
      ) : error && messages.length === 0 ? (
        /* Dedicated Error State if initial fetch fails */
        <div className="p-12 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-rose-500/20 text-center space-y-4 shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-base font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Failed to load support inquiries
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
              {error}
            </p>
          </div>
          <button
            type="button"
            onClick={fetchMessages}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>
        </div>
      ) : displayedMessages.length === 0 ? (
        /* Empty State */
        <div className="p-16 text-center bg-helios-card-light dark:bg-helios-card-dark rounded-xl border border-helios-border-light dark:border-helios-border-dark shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-black/5 dark:bg-white/5 flex items-center justify-center mx-auto mb-3 text-slate-400">
            <Inbox className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            {sourceFilter === 'flagged'
              ? 'No flagged escalations found'
              : statusFilter !== 'all'
              ? `No messages currently marked as '${statusFilter}'`
              : 'Your inbox is clear!'}
          </h3>
          <p className="text-sm text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 max-w-sm mx-auto">
            {sourceFilter === 'flagged'
              ? 'Team Member flagged operational escalations will appear here.'
              : statusFilter !== 'all'
              ? 'Try switching to "All" status to see resolved or open tickets.'
              : 'Any incoming customer inquiries or pipeline flags will appear here.'}
          </p>
          {(statusFilter !== 'all' || sourceFilter !== 'all') && (
            <button
              type="button"
              onClick={() => {
                setStatusFilter('all');
                setSourceFilter('all');
              }}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5 transition"
            >
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      ) : (
        /* Message Card List */
        <div className="space-y-4">
          {displayedMessages.map((item) => {
            const isOpen = (item.status || '').toLowerCase() === 'open';
            const isFlagged =
              (item.message_source || '').toLowerCase().trim() === 'team_member';

            return (
              <div
                key={item.message_id}
                className={`p-5 rounded-xl bg-helios-card-light dark:bg-helios-card-dark border transition-all duration-150 shadow-xs ${
                  isFlagged
                    ? isOpen
                      ? 'border-l-4 border-l-rose-500 border-rose-500/30 bg-rose-500/[0.02] dark:bg-rose-950/10 shadow-sm'
                      : 'border-l-4 border-l-rose-400/50 border-helios-border-light dark:border-helios-border-dark opacity-80 hover:opacity-100'
                    : isOpen
                    ? 'border-l-4 border-l-blue-500 border-helios-border-light dark:border-helios-border-dark'
                    : 'border-l-4 border-l-emerald-500/50 border-helios-border-light dark:border-helios-border-dark opacity-80 hover:opacity-100'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Message Content & Metadata */}
                  <div className="space-y-3 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Flagged Escalation vs SMB Request Source Badge */}
                      {isFlagged ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 shadow-xs">
                          <Flag className="w-3.5 h-3.5 text-rose-500 fill-current" />
                          <span>Flagged Escalation</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                          <span>Organization Inquiry</span>
                        </span>
                      )}

                      {/* Organization Tag */}
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-black/5 dark:bg-white/5 border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>{item.tenant_name || `Organization #${item.tenant_id}`}</span>
                      </span>

                      {/* Optional Batch Tag */}
                      {item.batch_id && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                          <Layers className="w-3 h-3 text-purple-500" />
                          <span>Batch {item.batch_id}</span>
                        </span>
                      )}

                      {/* Sender Info */}
                      <span className="inline-flex items-center gap-1 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {isFlagged ? (
                          <span className="font-semibold text-rose-600 dark:text-rose-400">
                            {item.from_user_name || 'Team Member'} (Ops)
                          </span>
                        ) : (
                          <span>
                            {item.from_user_name ? `${item.from_user_name} (Organization Owner)` : 'Organization Owner'}
                          </span>
                        )}
                      </span>

                      {/* Recipient Info */}
                      {item.to_user_name && (
                        <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                          <ArrowRight className="w-3 h-3 text-slate-400" />
                          <span>To: <strong>{item.to_user_name}</strong></span>
                        </span>
                      )}

                      {/* Status Indicator Badge */}
                      {isOpen ? (
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ml-auto md:ml-0 ${
                            isFlagged
                              ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                              : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                          }`}
                        >
                          <Clock className="w-3 h-3 text-amber-500" />
                          <span>Open</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 ml-auto md:ml-0">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                          <span>Resolved</span>
                        </span>
                      )}
                    </div>

                    {/* Message Body */}
                    <div
                      className={`p-4 rounded-xl border text-xs sm:text-sm whitespace-pre-wrap leading-relaxed ${
                        isFlagged
                          ? 'bg-rose-500/[0.04] dark:bg-rose-950/20 border-rose-500/20 text-helios-text-primary-light dark:text-helios-text-primary-dark font-sans'
                          : 'bg-black/[0.02] dark:bg-white/[0.02] border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark'
                      }`}
                    >
                      {item.message}
                    </div>

                    {/* Timestamps */}
                    <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex flex-wrap items-center gap-4 pt-0.5">
                      <span>Submitted: {formatDateTimeIN(item.created_at)}</span>
                      {item.resolved_at && (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          Resolved: {formatDateTimeIN(item.resolved_at)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Button: Mark Resolved */}
                  <div className="shrink-0 self-end md:self-center">
                    {isOpen ? (
                      <button
                        type="button"
                        onClick={() => handleResolve(item.message_id)}
                        disabled={resolvingId === item.message_id}
                        className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg text-white transition-all shadow-sm active:scale-95 disabled:opacity-50 cursor-pointer ${
                          isFlagged
                            ? 'bg-rose-600 hover:bg-rose-700 focus:ring-2 focus:ring-rose-500/40'
                            : 'bg-emerald-600 hover:bg-emerald-700 focus:ring-2 focus:ring-emerald-500/40'
                        }`}
                        title="Mark this inquiry or escalation as resolved"
                      >
                        <CheckCheck
                          className={`w-4 h-4 ${resolvingId === item.message_id ? 'animate-spin' : ''}`}
                        />
                        <span>{resolvingId === item.message_id ? 'Resolving...' : 'Mark Resolved'}</span>
                      </button>
                    ) : (
                      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Resolved</span>
                      </div>
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
