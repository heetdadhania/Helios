/**
 * Application-wide feature flags derived from environment variables.
 * Missing or unset variables strictly default to FALSE (hidden).
 * A feature is only enabled if the environment variable is explicitly string "true".
 */
const rawDbEnv =
  typeof import.meta !== 'undefined' && import.meta.env
    ? (import.meta.env.VITE_ENABLE_DB_CONNECTION ?? (import.meta.env as any).ENABLE_DB_CONNECTION)
    : undefined;

export const ENABLE_DB_CONNECTION: boolean =
  String(rawDbEnv ?? '').toLowerCase().trim() === 'true';
