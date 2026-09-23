import React, { useEffect, useState, useMemo } from 'react';
import {
  Database,
  Server,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  HardDrive,
  Lock,
  Layers,
  Terminal,
  Zap,
  Clock,
  Eye,
  EyeOff,
  X,
} from 'lucide-react';
import {
  SupportedDbType,
  DbTypeOption,
  DbConnectionCreate,
  DbConnectionOut,
  ToastNotification,
} from '@/types/dbConnection';
import { dbConnectionService } from '@/services/dbConnectionService';

const DB_TYPE_OPTIONS: DbTypeOption[] = [
  {
    value: 'postgresql',
    label: 'PostgreSQL',
    defaultPort: 5432,
    description: 'PostgreSQL 12+ with TLS (sslmode=prefer/require)',
  },
  {
    value: 'mysql',
    label: 'MySQL',
    defaultPort: 3306,
    description: 'MySQL 5.7 / 8.0+ with SSL encrypted transport',
  },
  {
    value: 'sqlserver',
    label: 'Microsoft SQL Server',
    defaultPort: 1433,
    description: 'SQL Server 2017+ with TLS encryption',
  },
];

export const ConnectDatabase: React.FC = () => {
  // Form State
  const [dbType, setDbType] = useState<SupportedDbType>('postgresql');
  const [host, setHost] = useState<string>('');
  const [port, setPort] = useState<number>(5432);
  const [databaseName, setDatabaseName] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [tableOrQuery, setTableOrQuery] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);

  // Connection testing and saving state
  const [isTested, setIsTested] = useState<boolean>(false);
  const [testResultMessage, setTestResultMessage] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Connections list state
  const [connections, setConnections] = useState<DbConnectionOut[]>([]);
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [syncingConnectionId, setSyncingConnectionId] = useState<number | null>(null);

  // Toast State
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const addToast = (type: 'success' | 'error' | 'info' | 'warning', title: string, message: string) => {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 6);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 6000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Load existing connections on mount
  const loadConnections = async () => {
    try {
      setIsLoadingList(true);
      const data = await dbConnectionService.listConnections();
      setConnections(data);
    } catch (err: any) {
      addToast('error', 'Failed to load connections', err.message || 'Could not fetch saved database connections.');
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    loadConnections();
  }, []);

  // Update default port when engine changes
  const handleDbTypeChange = (newType: SupportedDbType) => {
    setDbType(newType);
    const option = DB_TYPE_OPTIONS.find((o) => o.value === newType);
    if (option) {
      setPort(option.defaultPort);
    }
    // Invalidate prior test upon configuration change
    setIsTested(false);
    setTestResultMessage(null);
  };

  // Invalidate test whenever connection credentials/params change
  const handleFieldChange = (setter: (val: any) => void, val: any) => {
    setter(val);
    if (isTested) {
      setIsTested(false);
      setTestResultMessage(null);
    }
  };

  // Validate form completeness
  const isFormComplete = useMemo(() => {
    return (
      host.trim().length > 0 &&
      port > 0 &&
      databaseName.trim().length > 0 &&
      username.trim().length > 0 &&
      password.length > 0 &&
      tableOrQuery.trim().length > 0
    );
  }, [host, port, databaseName, username, password, tableOrQuery]);

  // Test Connection
  const handleTestConnection = async () => {
    if (!isFormComplete) {
      addToast('warning', 'Missing Fields', 'Please complete all required connection fields before testing.');
      return;
    }

    try {
      setIsTesting(true);
      const payload: DbConnectionCreate = {
        db_type: dbType,
        host: host.trim(),
        port: Number(port),
        database_name: databaseName.trim(),
        username: username.trim(),
        password: password,
        table_or_query: tableOrQuery.trim(),
      };

      const result = await dbConnectionService.testConnection(payload);
      if (result.success) {
        setIsTested(true);
        setTestResultMessage(result.message);
        addToast('success', 'Connection Verified', result.message);
      } else {
        setIsTested(false);
        setTestResultMessage(result.message);
        addToast('error', 'Connection Test Failed', result.message);
      }
    } catch (err: any) {
      setIsTested(false);
      const msg = err.message || 'Unexpected error while verifying connection.';
      setTestResultMessage(msg);
      addToast('error', 'Connection Error', msg);
    } finally {
      setIsTesting(false);
    }
  };

  // Save & Sync Now
  const handleSaveAndSync = async () => {
    if (!isTested) {
      addToast('warning', 'Test Required', 'You must successfully test the connection before saving.');
      return;
    }

    try {
      setIsSaving(true);
      const payload: DbConnectionCreate = {
        db_type: dbType,
        host: host.trim(),
        port: Number(port),
        database_name: databaseName.trim(),
        username: username.trim(),
        password: password,
        table_or_query: tableOrQuery.trim(),
        is_active: true,
      };

      // 1. Save connection & store secret in Databricks Secrets
      const savedConn = await dbConnectionService.saveConnection(payload);
      addToast('success', 'Connection Saved', `Saved connector to ${savedConn.database_name}. Initiating extraction...`);

      // 2. Clear sensitive input password immediately from state
      setPassword('');
      setIsTested(false);
      setTestResultMessage(null);

      // 3. Immediately trigger Bronze sync
      try {
        setSyncingConnectionId(savedConn.connection_id);
        const syncResp = await dbConnectionService.syncNow(savedConn.connection_id);
        addToast(
          'success',
          'Sync Initiated',
          `Batch ${syncResp.batch_id.substring(0, 8)}... created and landed in Medallion Bronze.`
        );
      } catch (syncErr: any) {
        addToast('warning', 'Sync Notice', syncErr.message || 'Connection was saved, but background sync is pending.');
      } finally {
        setSyncingConnectionId(null);
      }

      // 4. Refresh connections list
      await loadConnections();
    } catch (err: any) {
      addToast('error', 'Save Failed', err.message || 'Could not save database connection.');
    } finally {
      setIsSaving(false);
    }
  };

  // Individual row Sync Now
  const handleRowSync = async (connectionId: number) => {
    try {
      setSyncingConnectionId(connectionId);
      const resp = await dbConnectionService.syncNow(connectionId);
      addToast(
        'success',
        'Sync Complete',
        `Extracted latest records. Medallion batch ID: ${resp.batch_id.substring(0, 8)}...`
      );
      await loadConnections();
    } catch (err: any) {
      addToast('error', 'Sync Failed', err.message || `Failed to sync connection ${connectionId}.`);
    } finally {
      setSyncingConnectionId(null);
    }
  };

  // Helper for Database Engine Badge & Icons
  const renderDbBadge = (type: string) => {
    const normalized = type.toLowerCase();
    if (normalized.includes('postgres')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-500 border border-blue-500/20">
          <HardDrive className="w-3.5 h-3.5 text-blue-500" />
          PostgreSQL
        </span>
      );
    }
    if (normalized.includes('mysql')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20">
          <Database className="w-3.5 h-3.5 text-amber-500" />
          MySQL
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
        <Server className="w-3.5 h-3.5 text-emerald-500" />
        SQL Server
      </span>
    );
  };

  // Format timestamp helper
  const formatTimestamp = (dateStr: string | null) => {
    if (!dateStr) return 'Never synced';
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Toast Notification Container */}
      <div className="fixed top-5 right-5 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start justify-between p-4 rounded-card border shadow-lg backdrop-blur-md transition-all duration-300 ${
              toast.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-100'
                : toast.type === 'error'
                ? 'bg-rose-950/90 border-rose-500/30 text-rose-100'
                : toast.type === 'warning'
                ? 'bg-amber-950/90 border-amber-500/30 text-amber-100'
                : 'bg-blue-950/90 border-blue-500/30 text-blue-100'
            }`}
          >
            <div className="flex items-start gap-3">
              {toast.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />}
              {toast.type === 'error' && <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />}
              {toast.type === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />}
              {toast.type === 'info' && <Zap className="w-5 h-5 text-blue-400 mt-0.5 shrink-0" />}
              <div>
                <h5 className="text-xs font-semibold uppercase tracking-wider">{toast.title}</h5>
                <p className="text-xs mt-0.5 opacity-90 break-words">{toast.message}</p>
              </div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-white/60 hover:text-white ml-2 p-1"
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2.5">
            <Database className="w-6 h-6 text-helios-accent-blue" />
            Database Connection Ingestion
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1">
            Connect your MySQL, PostgreSQL, or Microsoft SQL Server database to pull live tables into Helios Medallion Bronze.
          </p>
        </div>

        {/* Security Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark shadow-sm">
          <ShieldCheck className="w-4 h-4 text-helios-accent-teal" />
          <span>Encrypted via Databricks Secrets & TLS</span>
        </div>
      </div>

      {/* Security Reassurance Callout */}
      <div className="p-4 rounded-card bg-helios-accent-blue/5 border border-helios-accent-blue/20 flex items-start gap-3">
        <Lock className="w-5 h-5 text-helios-accent-blue shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Zero-Knowledge Credential Security
          </p>
          <p className="text-helios-text-secondary-light dark:text-helios-text-secondary-dark leading-relaxed">
            Your database password is sent straight to Databricks Secrets using dedicated per-tenant scopes. Passwords are
            never stored in platform database tables, never logged, and never returned in API payloads.
          </p>
        </div>
      </div>

      {/* Connection Form Card */}
      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-6">
        <div className="border-b border-helios-border-light dark:border-helios-border-dark pb-4">
          <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Configure Remote Database Connection
          </h3>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Provide the host details and extraction query. Test the connection before saving.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSaveAndSync();
          }}
          className="space-y-5"
        >
          {/* Row 1: Engine Type & Port */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label
                htmlFor="db_type_select"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Database Engine Type *
              </label>
              <select
                id="db_type_select"
                value={dbType}
                onChange={(e) => handleDbTypeChange(e.target.value as SupportedDbType)}
                className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
              >
                {DB_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} — {opt.description}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="port_input"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Port *
              </label>
              <input
                id="port_input"
                type="number"
                min={1}
                max={65535}
                value={port}
                onChange={(e) => handleFieldChange(setPort, parseInt(e.target.value) || 0)}
                placeholder="5432"
                className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                required
              />
            </div>
          </div>

          {/* Row 2: Host & Database Name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="host_input"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Host / Server Address *
              </label>
              <div className="relative">
                <input
                  id="host_input"
                  type="text"
                  value={host}
                  onChange={(e) => handleFieldChange(setHost, e.target.value)}
                  placeholder="db.yourdomain.com or 192.168.1.100"
                  className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue font-mono"
                  required
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="database_name_input"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Database Name *
              </label>
              <input
                id="database_name_input"
                type="text"
                value={databaseName}
                onChange={(e) => handleFieldChange(setDatabaseName, e.target.value)}
                placeholder="production_db"
                className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                required
              />
            </div>
          </div>

          {/* Row 3: Username & Password */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="username_input"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Username *
              </label>
              <input
                id="username_input"
                type="text"
                value={username}
                onChange={(e) => handleFieldChange(setUsername, e.target.value)}
                placeholder="helios_reader"
                className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                required
              />
            </div>

            <div>
              <label
                htmlFor="password_input"
                className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
              >
                Password * (Masked & Encrypted)
              </label>
              <div className="relative">
                <input
                  id="password_input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => handleFieldChange(setPassword, e.target.value)}
                  placeholder="••••••••••••••••"
                  autoComplete="new-password"
                  className="w-full text-xs px-3.5 py-2.5 pr-10 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          {/* Row 4: Table or Query Name */}
          <div>
            <label
              htmlFor="table_or_query_input"
              className="block text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark mb-1.5"
            >
              Table Name or Custom SELECT Query *
            </label>
            <textarea
              id="table_or_query_input"
              rows={2}
              value={tableOrQuery}
              onChange={(e) => handleFieldChange(setTableOrQuery, e.target.value)}
              placeholder="e.g. orders, or SELECT id, customer_id, total, created_at FROM sales WHERE is_valid = 1"
              className="w-full text-xs px-3.5 py-2.5 rounded-control border border-helios-border-light dark:border-helios-border-dark bg-white dark:bg-neutral-900 text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-2 focus:ring-helios-accent-blue font-mono"
              required
            />
            <p className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-1 flex items-center gap-1">
              <Terminal className="w-3.5 h-3.5" />
              Specify either a single table name or an extraction query.
            </p>
          </div>

          {/* Test Status Banner */}
          {testResultMessage && (
            <div
              className={`p-3.5 rounded-control text-xs flex items-center justify-between border ${
                isTested
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
              }`}
            >
              <div className="flex items-center gap-2.5">
                {isTested ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
                <span>{testResultMessage}</span>
              </div>
              {isTested && (
                <span className="text-[11px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/20">
                  Ready to Save
                </span>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-helios-border-light dark:border-helios-border-dark">
            <div className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
              {isTested ? (
                <span className="text-emerald-500 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connection tested successfully. You can now save.
                </span>
              ) : (
                <span>Click &quot;Test Connection&quot; to verify credentials before saving.</span>
              )}
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <button
                type="button"
                id="test-connection-btn"
                onClick={handleTestConnection}
                disabled={isTesting || !isFormComplete}
                className="flex-1 sm:flex-initial px-4 py-2.5 text-xs font-semibold rounded-control border border-helios-accent-blue text-helios-accent-blue hover:bg-helios-accent-blue/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isTesting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Testing Connection...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    <span>Test Connection</span>
                  </>
                )}
              </button>

              <button
                type="submit"
                id="save-sync-btn"
                disabled={!isTested || isSaving}
                className="flex-1 sm:flex-initial px-5 py-2.5 text-xs font-semibold rounded-control bg-helios-accent-teal text-white hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
              >
                {isSaving ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving & Syncing...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Save & Sync Now</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Previously Connected Databases Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark flex items-center gap-2">
              <Layers className="w-4 h-4 text-helios-accent-blue" />
              Connected Databases ({connections.length})
            </h3>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
              Live managed databases feeding into your tenant's Medallion Bronze tables.
            </p>
          </div>
          <button
            type="button"
            onClick={loadConnections}
            disabled={isLoadingList}
            className="p-1.5 rounded-control text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:text-helios-text-primary-light dark:hover:text-helios-text-primary-dark hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors"
            title="Refresh connection list"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingList ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {isLoadingList ? (
          <div className="p-8 text-center rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-helios-accent-blue mb-2" />
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
              Loading registered database connections...
            </p>
          </div>
        ) : connections.length === 0 ? (
          <div className="p-8 text-center rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-2">
            <Database className="w-8 h-8 mx-auto text-helios-text-secondary-light dark:text-helios-text-secondary-dark opacity-50 mb-1" />
            <h4 className="text-xs font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">
              No database connections configured yet
            </h4>
            <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-sm mx-auto">
              Use the form above to connect your first PostgreSQL, MySQL, or SQL Server database.
            </p>
          </div>
        ) : (
          <div className="rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-helios-border-light dark:border-helios-border-dark bg-neutral-50 dark:bg-neutral-900/50 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    <th className="py-3 px-4 font-semibold">Engine</th>
                    <th className="py-3 px-4 font-semibold">Host & Port</th>
                    <th className="py-3 px-4 font-semibold">Database / User</th>
                    <th className="py-3 px-4 font-semibold">Table / Extraction</th>
                    <th className="py-3 px-4 font-semibold">Last Synced</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark">
                  {connections.map((conn) => (
                    <tr
                      key={conn.connection_id}
                      className="hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors"
                    >
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {renderDbBadge(conn.db_type)}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-medium text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        <div>{conn.host}</div>
                        <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark font-normal">
                          Port {conn.port}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-helios-text-primary-light dark:text-helios-text-primary-dark">
                        <div className="font-semibold">{conn.database_name}</div>
                        <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          User: {conn.username}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark max-w-xs truncate" title={conn.table_or_query}>
                        {conn.table_or_query}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark" />
                          <span>{formatTimestamp(conn.last_synced_at)}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          id={`sync-btn-${conn.connection_id}`}
                          onClick={() => handleRowSync(conn.connection_id)}
                          disabled={syncingConnectionId === conn.connection_id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-helios-accent-blue/10 text-helios-accent-blue hover:bg-helios-accent-blue hover:text-white disabled:opacity-50 transition-colors text-xs font-semibold"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${
                              syncingConnectionId === conn.connection_id ? 'animate-spin' : ''
                            }`}
                          />
                          <span>
                            {syncingConnectionId === conn.connection_id ? 'Syncing...' : 'Sync Now'}
                          </span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
