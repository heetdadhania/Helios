/**
 * Application-wide feature flags derived from Vite environment variables.
 */
export const ENABLE_DB_CONNECTION: boolean =
  import.meta.env.VITE_ENABLE_DB_CONNECTION === 'true';

