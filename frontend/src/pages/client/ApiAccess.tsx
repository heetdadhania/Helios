import React, { useEffect, useState } from 'react';
import {
  Key,
  ShieldAlert,
  Copy,
  Check,
  RefreshCw,
  Clock,
  Terminal,
  AlertTriangle,
  Code2,
  Lock,
  Calendar,
  CheckCircle2,
  X,
} from 'lucide-react';
import { ApiKeyInfo, ApiKeyGenerated } from '@/types/apiKey';
import { apiKeyService } from '@/services/apiKeyService';

export const ApiAccess: React.FC = () => {
  const [apiKeyInfo, setApiKeyInfo] = useState<ApiKeyInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRegenerating, setIsRegenerating] = useState<boolean>(false);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

  // One-time display of newly generated key
  const [newlyGeneratedKey, setNewlyGeneratedKey] = useState<ApiKeyGenerated | null>(null);

  // Copy button feedback
  const [copiedKey, setCopiedKey] = useState<boolean>(false);
  const [copiedSnippet, setCopiedSnippet] = useState<boolean>(false);

  // Code snippet tab selection
  const [activeSnippetTab, setActiveSnippetTab] = useState<'curl' | 'python' | 'javascript'>('curl');

  // Load API Key on component mount
  const fetchKeyInfo = async () => {
    try {
      setIsLoading(true);
      const data = await apiKeyService.getApiKeyInfo();
      setApiKeyInfo(data);
    } catch (err) {
      console.error('Failed to load API key info:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKeyInfo();
  }, []);

  // Handle regeneration confirmation
  const handleConfirmRegenerate = async () => {
    setShowConfirmModal(false);
    try {
      setIsRegenerating(true);
      const generated = await apiKeyService.regenerateApiKey();
      setNewlyGeneratedKey(generated);
      // Update persistent info with masked key
      setApiKeyInfo({
        api_key_id: generated.api_key_id,
        tenant_id: generated.tenant_id,
        masked_key: generated.masked_key,
        created_at: generated.created_at,
        last_used_at: null,
        is_active: true,
      });
    } catch (err: any) {
      alert(err.message || 'Failed to regenerate API key.');
    } finally {
      setIsRegenerating(false);
    }
  };

  // Copy to clipboard helper
  const handleCopy = (text: string, setCopiedState: (v: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setCopiedState(true);
    setTimeout(() => {
      setCopiedState(false);
    }, 2500);
  };

  // Format date helper
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never used';
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Code snippets for developers
  const displayKey = newlyGeneratedKey?.api_key || apiKeyInfo?.masked_key || 'helios_live_••••••••••••••••';

  const curlSnippet = `curl -X POST "https://api.helios.io/api/ingest" \\
  -H "Content-Type: application/json" \\
  -H "X-Helios-Api-Key: ${displayKey}" \\
  -d '{
    "records": [
      {
        "order_id": "ORD-98214",
        "customer_id": "CUST-402",
        "amount": 149.99,
        "status": "shipped",
        "ordered_at": "2026-09-23T10:15:00Z"
      }
    ]
  }'`;

  const pythonSnippet = `import requests

url = "https://api.helios.io/api/ingest"
headers = {
    "Content-Type": "application/json",
    "X-Helios-Api-Key": "${displayKey}"
}
payload = {
    "records": [
        {
            "order_id": "ORD-98214",
            "customer_id": "CUST-402",
            "amount": 149.99,
            "status": "shipped",
            "ordered_at": "2026-09-23T10:15:00Z"
        }
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code, response.json())`;

  const jsSnippet = `const url = "https://api.helios.io/api/ingest";

const response = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Helios-Api-Key": "${displayKey}"
  },
  body: JSON.stringify({
    records: [
      {
        order_id: "ORD-98214",
        customer_id: "CUST-402",
        amount: 149.99,
        status: "shipped",
        ordered_at: "2026-09-23T10:15:00Z"
      }
    ]
  })
});

const data = await response.json();
console.log(data);`;

  const activeSnippet =
    activeSnippetTab === 'curl'
      ? curlSnippet
      : activeSnippetTab === 'python'
      ? pythonSnippet
      : jsSnippet;

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2.5">
            <Key className="w-6 h-6 text-helios-accent-blue" />
            Programmatic API Access
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Authenticate external scripts, CRON jobs, and ERP integrations directly into Helios via API Push.
          </p>
        </div>

        {/* Security Shield Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark shadow-sm">
          <Lock className="w-4 h-4 text-helios-accent-teal" />
          <span>One-Way Cryptographic Hash Storage (SHA-256)</span>
        </div>
      </div>

      {/* Security Callout */}
      <div className="p-4 rounded-card bg-amber-500/10 border border-amber-500/20 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Zero-Knowledge Key Storage
          </p>
          <p className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark leading-relaxed">
            For security, Helios never stores your raw API key in plaintext. Only an irreversible SHA-256 hash is
            retained. The full raw key is shown only once when generated.
          </p>
        </div>
      </div>

      {/* NEWLY GENERATED KEY BANNER (Shown ONCE only) */}
      {newlyGeneratedKey && (
        <div className="p-6 rounded-card bg-emerald-950/40 border-2 border-emerald-500/60 shadow-lg space-y-4 animate-in fade-in duration-300">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-emerald-200">
                  New API Key Generated — Copy it now!
                </h4>
                <p className="text-xs text-emerald-300/80 mt-0.5">
                  This full secret key will <span className="font-semibold underline">never be shown again</span>.
                  Store it in your environment variables or secret manager immediately.
                </p>
              </div>
            </div>
            <button
              onClick={() => setNewlyGeneratedKey(null)}
              className="text-emerald-400 hover:text-white p-1 rounded-control hover:bg-emerald-900/50"
              title="Dismiss banner"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2 p-3 rounded-control bg-black/60 border border-emerald-500/30">
            <code className="flex-1 font-mono text-xs text-emerald-300 break-all select-all font-semibold">
              {newlyGeneratedKey.api_key}
            </code>
            <button
              type="button"
              onClick={() => handleCopy(newlyGeneratedKey.api_key, setCopiedKey)}
              className="px-3.5 py-1.5 rounded-control bg-emerald-500 text-black hover:bg-emerald-400 font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0 shadow-sm"
            >
              {copiedKey ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Key</span>
                </>
              )}
            </button>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setNewlyGeneratedKey(null)}
              className="px-4 py-1.5 text-xs font-semibold rounded-control text-emerald-200 hover:text-white hover:bg-emerald-900/40 transition-colors"
            >
              I have safely copied my key
            </button>
          </div>
        </div>
      )}

      {/* Active API Key Card */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-helios-border-light dark:border-helios-border-dark gap-3">
          <div>
            <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              Active Ingestion Key
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              Use this key in the <code className="font-mono text-helios-accent-blue font-medium">X-Helios-Api-Key</code> HTTP request header.
            </p>
          </div>

          <button
            type="button"
            id="regenerate-key-btn"
            onClick={() => setShowConfirmModal(true)}
            disabled={isRegenerating || isLoading}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-control border border-rose-500/40 text-rose-500 hover:bg-rose-500/10 disabled:opacity-50 transition-colors shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
            <span>Regenerate Key</span>
          </button>
        </div>

        {isLoading ? (
          <div className="p-6 text-center text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-helios-accent-blue" />
            <span>Retrieving key configuration...</span>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Masked Key Display Box */}
            <div>
              <label className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5">
                Current API Key (Masked)
              </label>
              <div className="flex items-center gap-2 p-3 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-neutral-50 dark:bg-neutral-900/60 font-mono text-xs">
                <span className="flex-1 text-helios-text-primary-light dark:text-helios-text-primary-dark tracking-wider select-all font-medium">
                  {apiKeyInfo?.masked_key || 'No active key generated'}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  Active
                </span>
              </div>
            </div>

            {/* Key Metadata Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              <div className="p-3.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900/40">
                <div className="flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  <Calendar className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium uppercase tracking-wider">Created</span>
                </div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatDate(apiKeyInfo?.created_at || null)}
                </div>
              </div>

              <div className="p-3.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900/40">
                <div className="flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium uppercase tracking-wider">Last Ingestion</span>
                </div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  {formatDate(apiKeyInfo?.last_used_at || null)}
                </div>
              </div>

              <div className="p-3.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900/40">
                <div className="flex items-center gap-2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark mb-1">
                  <Terminal className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium uppercase tracking-wider">Rate Limit</span>
                </div>
                <div className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  60 requests / min
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Developer Integration Code Snippets */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <Code2 className="w-4 h-4 text-helios-accent-blue" />
              API Push Integration Example
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              POST JSON records directly to <code className="font-mono text-helios-accent-blue font-medium">/api/ingest</code> using your API key.
            </p>
          </div>

          {/* Snippet Language Tabs */}
          <div className="flex items-center rounded-control bg-neutral-100 dark:bg-neutral-900 p-0.5 border border-helios-border-light dark:border-helios-border-dark">
            <button
              type="button"
              onClick={() => setActiveSnippetTab('curl')}
              className={`px-3 py-1 text-xs font-semibold rounded-[6px] transition-colors ${
                activeSnippetTab === 'curl'
                  ? 'bg-white dark:bg-neutral-800 text-helios-accent-blue shadow-sm'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              cURL
            </button>
            <button
              type="button"
              onClick={() => setActiveSnippetTab('python')}
              className={`px-3 py-1 text-xs font-semibold rounded-[6px] transition-colors ${
                activeSnippetTab === 'python'
                  ? 'bg-white dark:bg-neutral-800 text-helios-accent-blue shadow-sm'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              Python
            </button>
            <button
              type="button"
              onClick={() => setActiveSnippetTab('javascript')}
              className={`px-3 py-1 text-xs font-semibold rounded-[6px] transition-colors ${
                activeSnippetTab === 'javascript'
                  ? 'bg-white dark:bg-neutral-800 text-helios-accent-blue shadow-sm'
                  : 'text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark'
              }`}
            >
              JavaScript
            </button>
          </div>
        </div>

        {/* Code Snippet Box */}
        <div className="relative rounded-control overflow-hidden border border-neutral-800 bg-neutral-950 font-mono text-xs">
          <div className="flex items-center justify-between px-4 py-2 bg-neutral-900 border-b border-neutral-800 text-[11px] text-neutral-400">
            <span>
              {activeSnippetTab === 'curl'
                ? 'Terminal Bash / zsh'
                : activeSnippetTab === 'python'
                ? 'Python 3 (requests)'
                : 'Node.js (Fetch API)'}
            </span>
            <button
              type="button"
              onClick={() => handleCopy(activeSnippet, setCopiedSnippet)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 transition-colors text-[11px]"
            >
              {copiedSnippet ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Snippet</span>
                </>
              )}
            </button>
          </div>
          <pre className="p-4 overflow-x-auto text-neutral-200 leading-relaxed">
            <code>{activeSnippet}</code>
          </pre>
        </div>

        {/* Ingestion Specification Summary */}
        <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-helios-accent-teal"></span>
            <span>Batch processing lands automatically into Medallion Bronze tables.</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-helios-accent-blue"></span>
            <span>Accepts up to 10,000 JSON records / 10MB per HTTP push.</span>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-2xl space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-500 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
                  Regenerate API Key?
                </h4>
                <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 leading-relaxed">
                  Your current API key will <span className="font-semibold text-rose-500">stop working immediately</span>.
                  Any automated systems or integrations relying on the old key will fail until updated.
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-control border border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                id="confirm-regenerate-btn"
                onClick={handleConfirmRegenerate}
                className="px-4 py-2 text-xs font-semibold rounded-control bg-rose-600 text-white hover:bg-rose-700 transition-colors shadow-sm"
              >
                Yes, Regenerate Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
