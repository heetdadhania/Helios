import React, { useEffect, useState } from 'react';
import {
  MessageSquare,
  Send,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { supportService } from '@/services/supportService';
import { SupportMessage } from '@/types/support';
import { formatDateTimeIN } from '@/utils/currency';

export const ClientSupport: React.FC = () => {
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState<string>('');
  const [sending, setSending] = useState<boolean>(false);
  const [sendSuccess, setSendSuccess] = useState<boolean>(false);

  const fetchMessages = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await supportService.getMessages('all');
      setMessages(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load support inquiries.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    setSending(true);
    setError(null);
    try {
      await supportService.sendMessage(newMessage.trim());
      setNewMessage('');
      setSendSuccess(true);
      setTimeout(() => setSendSuccess(false), 5000);
      fetchMessages();
    } catch (err: any) {
      setError(err?.message || 'Failed to dispatch message to operations team.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-xl bg-helios-accent-blue/10 text-helios-accent-blue">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Organization Support & Inquiries
            </h1>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              Direct communication channel with your assigned operations specialists.
            </p>
          </div>
        </div>
      </div>

      {/* New Inquiry Form */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs">
        <h2 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-3">
          Submit a New Request or Inquiry
        </h2>

        {sendSuccess && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Your request has been routed to your assigned team member.</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-xs font-semibold text-rose-600 hover:underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleSendMessage} className="space-y-3">
          <textarea
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type your message, question, or data re-upload request here..."
            rows={3}
            className="w-full p-3 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-helios-bg-light dark:bg-helios-bg-dark text-helios-text-primary-light dark:text-helios-text-primary-dark text-xs focus:outline-hidden focus:ring-2 focus:ring-helios-accent-blue resize-none"
          />
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={sending || !newMessage.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg bg-helios-accent-blue text-white hover:bg-blue-600 transition shadow-sm disabled:opacity-50"
            >
              {sending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              <span>Send to Support</span>
            </button>
          </div>
        </form>
      </div>

      {/* Inquiry History */}
      <div className="p-6 rounded-2xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Past Inquiries ({messages.length})
          </h2>
          <button
            type="button"
            onClick={fetchMessages}
            disabled={loading}
            className="text-xs text-helios-accent-blue hover:underline flex items-center gap-1"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loading && (
          <div className="p-8 text-center text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-helios-accent-blue mb-2" />
            <p className="text-xs">Loading message history...</p>
          </div>
        )}

        {!loading && messages.length === 0 && (
          <div className="p-8 text-center border border-dashed border-helios-border-light dark:border-helios-border-dark rounded-xl">
            <MessageSquare className="w-8 h-8 mx-auto text-gray-400 mb-2" />
            <p className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No support inquiries submitted yet.
            </p>
          </div>
        )}

        {!loading && messages.length > 0 && (
          <div className="space-y-3">
            {messages.map((m) => (
              <div
                key={m.message_id}
                className="p-3.5 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-black/[0.02] dark:bg-white/[0.02]"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                    {m.from_user_name || 'Organization Owner'}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        m.status === 'open'
                          ? 'bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400'
                          : 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400'
                      }`}
                    >
                      {m.status}
                    </span>
                    <span className="text-[11px] text-gray-400">
                      {m.created_at ? formatDateTimeIN(m.created_at) : ''}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark whitespace-pre-wrap">
                  {m.message}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
