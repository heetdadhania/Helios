import React, { useState } from 'react';
import {
  MessageSquarePlus,
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { supportService } from '@/services/supportService';

interface ContactSupportButtonProps {
  className?: string;
  variant?: 'button' | 'navbar';
}

export const ContactSupportButton: React.FC<ContactSupportButtonProps> = ({
  className = '',
  variant = 'button',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ show: boolean; text: string }>({
    show: false,
    text: '',
  });

  const handleOpen = () => {
    setMessage('');
    setError(null);
    setIsOpen(true);
  };

  const handleClose = () => {
    if (!sending) {
      setIsOpen(false);
      setMessage('');
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) {
      setError('Please provide a message before sending.');
      return;
    }

    setSending(true);
    setError(null);

    try {
      await supportService.sendMessage(message.trim());
      setIsOpen(false);
      setMessage('');
      setToast({
        show: true,
        text: 'Your update request has been routed to your assigned operations team.',
      });
      setTimeout(() => {
        setToast({ show: false, text: '' });
      }, 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to dispatch message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {/* Trigger Button */}
      {variant === 'navbar' ? (
        <button
          type="button"
          onClick={handleOpen}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-control border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-helios-bg-light dark:hover:bg-helios-bg-dark transition shadow-xs ${className}`}
          title="Message your assigned support specialist"
        >
          <MessageSquarePlus className="w-3.5 h-3.5 text-helios-accent-blue" />
          <span className="hidden sm:inline">Contact Support</span>
        </button>
      ) : (
        <button
          type="button"
          onClick={handleOpen}
          className={`inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition shadow-sm ${className}`}
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>Contact / Request Update</span>
        </button>
      )}

      {/* Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div
            className="w-full max-w-lg bg-helios-card-light dark:bg-helios-card-dark rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
            role="dialog"
            aria-modal="true"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    Contact Assigned Support
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Direct inquiry routed to your organization's Helios specialist.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleClose}
                disabled={sending}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 flex items-center gap-2 text-red-700 dark:text-red-300 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 uppercase tracking-wider">
                  Message / Update Inquiry
                </label>
                <textarea
                  rows={5}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Describe your inquiry, request pipeline status verification, or ask a question regarding your recent data submissions..."
                  disabled={sending}
                  className="w-full p-3 text-sm rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  autoFocus
                />
                <p className="text-[11px] text-gray-400 mt-1">
                  Your inquiry is strictly routed to your assigned team member without exposing internal pipeline logs.
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={sending}
                  className="px-4 py-2 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sending || !message.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition shadow-sm"
                >
                  <Send className={`w-4 h-4 ${sending ? 'animate-pulse' : ''}`} />
                  <span>{sending ? 'Sending...' : 'Send Message'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Toast */}
      {toast.show && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md p-4 rounded-xl bg-gray-900 text-white dark:bg-gray-800 dark:border dark:border-gray-700 shadow-2xl flex items-start gap-3 animate-in slide-in-from-bottom-5 duration-200">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm font-medium">
            <div className="font-semibold text-white">Message Sent</div>
            <div className="text-gray-300 text-xs mt-0.5">{toast.text}</div>
          </div>
          <button
            type="button"
            onClick={() => setToast({ show: false, text: '' })}
            className="text-gray-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </>
  );
};

export default ContactSupportButton;
